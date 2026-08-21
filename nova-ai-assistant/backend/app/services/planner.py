import json
import logging
from typing import Optional, List
from pydantic import BaseModel, Field, ValidationError
from google.genai import types
from google.genai.errors import APIError

from app.services.gemini import get_gemini_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Strict Pydantic Schemas for Plan Validation
# ---------------------------------------------------------------------------

class PlanStep(BaseModel):
    step_number: int = Field(..., ge=1, description="1-based ordered step number")
    purpose: str = Field(..., description="Purpose or description of what this step accomplishes")
    tool: Optional[str] = Field(None, description="Name of the required tool if any, or null if no tool is needed")
    expected_result: str = Field(..., description="Expected output or state change resulting from this step")


class ExecutionPlan(BaseModel):
    summary: str = Field(..., description="High-level summary of the execution plan")
    steps: List[PlanStep] = Field(..., min_items=2, max_items=4, description="List of 2 to 4 ordered steps")


# Custom Exception for Planner Failures
class PlannerError(Exception):
    """Raised when plan generation or validation fails safely."""
    pass


# ---------------------------------------------------------------------------
# Planner Function
# ---------------------------------------------------------------------------

PLANNER_SYSTEM_INSTRUCTION = """
You are NOVA's Execution Planner AI.
Given a user command and relevant context, create a structured, step-by-step execution plan.

Rules:
1. The plan MUST contain between 2 and 4 ordered steps (min 2, max 4).
2. Each step must include step_number, purpose, tool (if required, otherwise null), and expected_result.
3. Keep the plan logical, minimal, and focused on fulfilling the user's intent.
"""


def generate_plan(
    command: str,
    context: Optional[str] = None,
    model_name: str = "gemini-3.6-flash",
) -> ExecutionPlan:
    """Generate a validated execution plan for a user command using Gemini.

    Args:
        command: The input command from the user.
        context: Optional relevant background context or memory.
        model_name: Gemini model to use (default: 'gemini-3.6-flash').

    Returns:
        ExecutionPlan: Validated Pydantic object containing 2-4 ordered steps.

    Raises:
        PlannerError: If prompt is invalid, Gemini call fails, or JSON output fails schema validation.
    """
    if not command or not command.strip():
        raise PlannerError("User command cannot be empty.")

    # Build prompt with optional context
    prompt_parts = [f"User Command: {command.strip()}"]
    if context and context.strip():
        prompt_parts.append(f"Relevant Context: {context.strip()}")
    full_prompt = "\n\n".join(prompt_parts)

    try:
        client = get_gemini_client()

        # Enforce structured JSON output via Pydantic response_schema
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=PLANNER_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ExecutionPlan,
                temperature=0.2,
            ),
        )

        if not response or not response.text:
            raise PlannerError("Gemini returned an empty response.")

        # Strict Validation using Pydantic
        raw_json = response.text.strip()
        plan = ExecutionPlan.model_validate_json(raw_json)

        # Enforce 2-4 steps constraint explicitly
        if not (2 <= len(plan.steps) <= 4):
            raise PlannerError(f"Plan must contain between 2 and 4 steps, but got {len(plan.steps)} steps.")

        return plan

    except ValidationError as ve:
        logger.error(f"Plan JSON schema validation failed: {ve}")
        raise PlannerError(f"Invalid plan format received from Gemini: {ve}") from ve
    except APIError as ae:
        logger.error(f"Gemini API error during planning: {ae}")
        raise PlannerError(f"Gemini API error: {ae.message}") from ae
    except Exception as e:
        logger.error(f"Unexpected error in planner module: {e}")
        raise PlannerError(f"Failed to generate plan: {str(e)}") from e
