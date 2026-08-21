from app.services.planner import ExecutionPlan, PlanStep
from app.services.executor import (
    PlanActVerifyExecutor,
    PlanStatus,
    StepStatus,
    MOCK_TOOL_REGISTRY,
)


def print_execution_summary(test_name: str, state):
    print(f"\n==========================================")
    print(f" {test_name}")
    print(f"==========================================")
    print(f"Command: '{state.command}'")
    print(f"Plan ID: {state.plan_id}")
    print(f"Overall Status: {state.status.value}")
    if state.error:
        print(f"Global Error: {state.error}")

    print("\nSTEP EXECUTIONS:")
    for s in state.steps:
        tool_str = f" [{s.tool}]" if s.tool else " [No Tool]"
        print(f"  Step {s.step_number}{tool_str} -> {s.status.value}")
        print(f"    Purpose: {s.purpose}")
        if s.action_output:
            print(f"    Action Output: {s.action_output}")
        if s.verification_reason:
            print(f"    Verification: {s.verification_reason}")
        if s.error:
            print(f"    Step Error: {s.error}")
    print("------------------------------------------")


def test_1_successful_plan():
    executor = PlanActVerifyExecutor()
    command = "Search for the latest Next.js 15 features and write a summary."
    state = executor.execute_command(command)

    print_execution_summary("TEST 1: Successful Plan -> Act -> Verify Execution", state)
    assert state.status == PlanStatus.COMPLETED, "Plan status should be COMPLETED"
    assert len(state.steps) >= 2, "Should have at least 2 steps"
    assert all(s.status == StepStatus.COMPLETED for s in state.steps), "All steps should be COMPLETED"
    print("[OK] Test 1 PASSED!")


def test_2_failed_plan():
    executor = PlanActVerifyExecutor()
    # Empty command causes planner to fail in PLAN phase
    state = executor.execute_command("")

    print_execution_summary("TEST 2: Failed Plan Phase (Empty Input)", state)
    assert state.status == PlanStatus.FAILED, "Plan status should be FAILED"
    assert "PLAN FAILED" in (state.error or ""), "Error should indicate PLAN FAILED"
    print("[OK] Test 2 PASSED!")


def test_3_failed_action():
    executor = PlanActVerifyExecutor()
    # Create a plan containing a tool that will fail ('failing_tool')
    forced_plan = ExecutionPlan(
        summary="Plan with a failing tool action",
        steps=[
            PlanStep(
                step_number=1,
                purpose="Step 1 succeeds",
                tool="web_search",
                expected_result="Valid search results",
            ),
            PlanStep(
                step_number=2,
                purpose="Step 2 tool execution crashes",
                tool="failing_tool",
                expected_result="Will not be reached",
            ),
            PlanStep(
                step_number=3,
                purpose="Step 3 should never be executed",
                tool="web_search",
                expected_result="Will not be reached",
            ),
        ],
    )

    state = executor.execute_command(
        command="Run task with broken tool", force_plan=forced_plan
    )

    print_execution_summary("TEST 3: Failed Action (Tool Execution Crash)", state)
    assert state.status == PlanStatus.FAILED, "Plan status should be FAILED"
    assert state.steps[0].status == StepStatus.COMPLETED, "Step 1 should be COMPLETED"
    assert state.steps[1].status == StepStatus.FAILED, "Step 2 should be FAILED"
    assert state.steps[2].status == StepStatus.PENDING, "Step 3 should remain PENDING (not executed)"
    assert "failing_tool" in (state.steps[1].error or ""), "Step 2 error should mention failing_tool"
    print("[OK] Test 3 PASSED!")


def test_4_failed_verification():
    executor = PlanActVerifyExecutor()
    # Create a plan containing a tool that returns invalid output format ('invalid_output_tool')
    forced_plan = ExecutionPlan(
        summary="Plan with invalid output failing verification",
        steps=[
            PlanStep(
                step_number=1,
                purpose="Step 1 succeeds",
                tool="web_search",
                expected_result="Valid search results",
            ),
            PlanStep(
                step_number=2,
                purpose="Step 2 returns invalid output failing verification",
                tool="invalid_output_tool",
                expected_result="Expected valid data",
            ),
            PlanStep(
                step_number=3,
                purpose="Step 3 should never be executed",
                tool="web_search",
                expected_result="Will not be reached",
            ),
        ],
    )

    state = executor.execute_command(
        command="Run task with invalid output tool", force_plan=forced_plan
    )

    print_execution_summary("TEST 4: Failed Verification (Invalid Tool Output)", state)
    assert state.status == PlanStatus.FAILED, "Plan status should be FAILED"
    assert state.steps[0].status == StepStatus.COMPLETED, "Step 1 should be COMPLETED"
    assert state.steps[1].status == StepStatus.FAILED, "Step 2 should be FAILED"
    assert state.steps[2].status == StepStatus.PENDING, "Step 3 should remain PENDING (not executed)"
    assert "Verification failed" in (state.steps[1].error or ""), "Step 2 error should cite Verification failed"
    print("[OK] Test 4 PASSED!")


def main():
    test_1_successful_plan()
    test_2_failed_plan()
    test_3_failed_action()
    test_4_failed_verification()
    print("\n==========================================")
    print(" ALL 4 PLAN-ACT-VERIFY TESTS PASSED SUCCESSFULLY! ")
    print("==========================================")


if __name__ == "__main__":
    main()
