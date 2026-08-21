import uuid
import time
import asyncio
import logging
from enum import Enum
from typing import Dict, Any, Callable, List, Optional, AsyncGenerator
from pydantic import BaseModel, Field

from app.services.planner import generate_plan, ExecutionPlan, PlanStep, PlannerError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Event Types
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    PLAN = "PLAN"
    TOOL_CALL = "TOOL_CALL"
    EVIDENCE = "EVIDENCE"
    DECISION = "DECISION"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"


class StepStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PlanStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StepExecutionRecord(BaseModel):
    step_number: int
    purpose: str
    tool: Optional[str] = None
    expected_result: str
    status: StepStatus = StepStatus.PENDING
    action_output: Optional[Any] = None
    verification_reason: Optional[str] = None
    error: Optional[str] = None


class PlanExecutionState(BaseModel):
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    command: str
    summary: str = ""
    status: PlanStatus = PlanStatus.PENDING
    steps: List[StepExecutionRecord] = []
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Mock Tool Registry (Expandable to Real Tools Later)
# ---------------------------------------------------------------------------

ToolHandler = Callable[[Dict[str, Any]], Dict[str, Any]]

def _mock_web_search(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "data": "Top search results retrieved for query."}

def _mock_database_query(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "records": [{"id": 1, "task": "pending_job"}]}

def _mock_email_notification(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "delivered": True, "message_id": "msg_998877"}

def _mock_financial_calculator(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "monthly_payment": 1798.65, "currency": "USD"}

def _mock_failing_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    raise RuntimeError("Tool execution failed: Connection refused to remote API.")

def _mock_invalid_output_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "error", "error_code": "INVALID_RESPONSE_FORMAT", "data": None}


MOCK_TOOL_REGISTRY: Dict[str, ToolHandler] = {
    "web_search": _mock_web_search,
    "database_query_tool": _mock_database_query,
    "database_task_query_tool": _mock_database_query,
    "email_notification_tool": _mock_email_notification,
    "financial_calculator": _mock_financial_calculator,
    "calculator": _mock_financial_calculator,
    "failing_tool": _mock_failing_tool,
    "invalid_output_tool": _mock_invalid_output_tool,
}


# ---------------------------------------------------------------------------
# Verification Logic (VERIFY)
# ---------------------------------------------------------------------------

def verify_step_execution(step: PlanStep, output: Any) -> tuple[bool, str]:
    if output is None:
        return False, "Step produced no output (None)."

    if isinstance(output, dict):
        if output.get("status") == "error":
            return False, f"Tool reported error: {output.get('error_code', 'Unknown error')}"

    return True, f"Output verified against expected result: '{step.expected_result[:60]}...'"


# ---------------------------------------------------------------------------
# Plan -> Act -> Verify Executor Engine
# ---------------------------------------------------------------------------

class PlanActVerifyExecutor:
    """Orchestrates Plan -> Act -> Verify loop with both sync & async event streaming."""

    def __init__(self, tool_registry: Optional[Dict[str, ToolHandler]] = None):
        self.tool_registry = tool_registry if tool_registry is not None else MOCK_TOOL_REGISTRY

    def execute_command(
        self,
        command: str,
        context: Optional[str] = None,
        force_plan: Optional[ExecutionPlan] = None,
    ) -> PlanExecutionState:
        # Synchronous execution method
        if force_plan:
            plan = force_plan
        else:
            try:
                plan = generate_plan(command=command, context=context)
            except PlannerError as pe:
                return PlanExecutionState(
                    command=command,
                    status=PlanStatus.FAILED,
                    error=f"PLAN FAILED: {str(pe)}",
                )

        state = PlanExecutionState(
            command=command,
            summary=plan.summary,
            status=PlanStatus.IN_PROGRESS,
            steps=[
                StepExecutionRecord(
                    step_number=s.step_number,
                    purpose=s.purpose,
                    tool=s.tool,
                    expected_result=s.expected_result,
                    status=StepStatus.PENDING,
                )
                for s in plan.steps
            ],
        )

        if not state.steps:
            state.status = PlanStatus.FAILED
            state.error = "Unvalidated plan: zero steps present."
            return state

        for step_def, step_rec in zip(plan.steps, state.steps):
            step_rec.status = StepStatus.IN_PROGRESS
            tool_name = step_def.tool

            if tool_name:
                handler = self.tool_registry.get(tool_name)
                if not handler:
                    action_output = {"status": "success", "data": f"Executed mock handler for tool '{tool_name}'"}
                else:
                    try:
                        action_output = handler({"command": command, "step": step_def.step_number})
                    except Exception as exc:
                        err_msg = f"Tool '{tool_name}' crashed: {str(exc)}"
                        step_rec.status = StepStatus.FAILED
                        step_rec.error = err_msg
                        state.status = PlanStatus.FAILED
                        state.error = f"Execution stopped at Step {step_rec.step_number} due to tool failure."
                        return state
            else:
                action_output = {"status": "success", "data": f"Synthesized output for '{step_def.purpose}'"}

            step_rec.action_output = action_output

            is_valid, reason = verify_step_execution(step_def, action_output)
            step_rec.verification_reason = reason

            if not is_valid:
                err_msg = f"Verification failed: {reason}"
                step_rec.status = StepStatus.FAILED
                step_rec.error = err_msg
                state.status = PlanStatus.FAILED
                state.error = f"Execution stopped at Step {step_rec.step_number} due to verification failure."
                return state

            step_rec.status = StepStatus.COMPLETED

        state.status = PlanStatus.COMPLETED
        return state

    async def execute_command_stream(
        self,
        command: str,
        context: Optional[str] = None,
        force_plan: Optional[ExecutionPlan] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Asynchronously stream Plan -> Act -> Verify live execution events.

        Yields clean, safe event dicts for WebSocket consumers:
          - PLAN: Generated plan summary and steps list
          - TOOL_CALL: Invocation of tool for a step
          - EVIDENCE: Action output / data collected
          - DECISION: Step verification result
          - SUCCESS: Overall plan completion
          - ERROR: Failure details at plan, action, or verification stage
        """
        def make_event(event_type: EventType, payload: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "event": event_type.value,
                "timestamp": time.time(),
                "data": payload,
            }

        # 1. PLAN Phase
        if force_plan:
            plan = force_plan
        else:
            try:
                # Run plan generation in executor thread to prevent blocking event loop
                plan = await asyncio.to_thread(generate_plan, command, context)
            except PlannerError as pe:
                yield make_event(
                    EventType.ERROR,
                    {"stage": "PLAN", "error": f"Plan generation failed: {str(pe)}"},
                )
                return

        plan_id = str(uuid.uuid4())
        yield make_event(
            EventType.PLAN,
            {
                "plan_id": plan_id,
                "summary": plan.summary,
                "steps_count": len(plan.steps),
                "steps": [
                    {
                        "step_number": s.step_number,
                        "purpose": s.purpose,
                        "tool": s.tool,
                        "expected_result": s.expected_result,
                    }
                    for s in plan.steps
                ],
            },
        )
        await asyncio.sleep(0.1)

        # 2. ACT & VERIFY Loop
        for step_def in plan.steps:
            # Emit TOOL_CALL
            tool_name = step_def.tool or "system_reasoning"
            yield make_event(
                EventType.TOOL_CALL,
                {
                    "plan_id": plan_id,
                    "step_number": step_def.step_number,
                    "tool": tool_name,
                    "purpose": step_def.purpose,
                },
            )
            await asyncio.sleep(0.2)

            # ACT
            action_output = None
            if step_def.tool:
                handler = self.tool_registry.get(step_def.tool)
                if not handler:
                    action_output = {"status": "success", "data": f"Executed mock handler for tool '{step_def.tool}'"}
                else:
                    try:
                        action_output = await asyncio.to_thread(
                            handler, {"command": command, "step": step_def.step_number}
                        )
                    except Exception as exc:
                        err_msg = f"Tool '{step_def.tool}' crashed: {str(exc)}"
                        yield make_event(
                            EventType.ERROR,
                            {
                                "plan_id": plan_id,
                                "stage": "ACT",
                                "step_number": step_def.step_number,
                                "tool": step_def.tool,
                                "error": err_msg,
                            },
                        )
                        return
            else:
                action_output = {"status": "success", "data": f"Synthesized output for '{step_def.purpose}'"}

            # Emit EVIDENCE
            yield make_event(
                EventType.EVIDENCE,
                {
                    "plan_id": plan_id,
                    "step_number": step_def.step_number,
                    "tool": tool_name,
                    "output": action_output,
                },
            )
            await asyncio.sleep(0.2)

            # VERIFY
            is_valid, reason = verify_step_execution(step_def, action_output)
            yield make_event(
                EventType.DECISION,
                {
                    "plan_id": plan_id,
                    "step_number": step_def.step_number,
                    "passed": is_valid,
                    "reason": reason,
                },
            )
            await asyncio.sleep(0.1)

            if not is_valid:
                yield make_event(
                    EventType.ERROR,
                    {
                        "plan_id": plan_id,
                        "stage": "VERIFY",
                        "step_number": step_def.step_number,
                        "error": f"Verification failed: {reason}",
                    },
                )
                return

        # 3. SUCCESS
        yield make_event(
            EventType.SUCCESS,
            {
                "plan_id": plan_id,
                "message": "Execution plan completed successfully.",
            },
        )
