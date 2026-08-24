import json
from app.services.planner import generate_plan, PlannerError


def print_plan(test_num: int, command: str, context: str | None, plan):
    print(f"\n==========================================")
    print(f" TEST {test_num}: {command}")
    if context:
        print(f" Context: {context}")
    print(f"==========================================")
    print(f"SUMMARY: {plan.summary}\n")
    print("STEPS:")
    for step in plan.steps:
        tool_str = f" [Tool: {step.tool}]" if step.tool else " [No Tool Needed]"
        print(f"  Step {step.step_number}:{tool_str}")
        print(f"    Purpose: {step.purpose}")
        print(f"    Expected Result: {step.expected_result}")
    print("------------------------------------------")


def main():
    test_cases = [
        {
            "command": "Search for the latest Next.js 15 features and write a summary.",
            "context": None,
        },
        {
            "command": "Check my database tasks for any pending jobs and notify me.",
            "context": "User ID: usr_12345, Notification Channel: Email",
        },
        {
            "command": "Calculate the monthly payment for a $300,000 mortgage at 6% interest over 30 years.",
            "context": "User location: US, currency: USD",
        },
    ]

    for idx, tc in enumerate(test_cases, 1):
        try:
            plan = generate_plan(command=tc["command"], context=tc["context"])
            print_plan(idx, tc["command"], tc["context"], plan)
        except PlannerError as pe:
            print(f"❌ Test {idx} Failed safely with PlannerError: {pe}")
        except Exception as e:
            print(f"❌ Test {idx} Unexpected Error: {e}")

    # Test Error Handling for Invalid Prompt / Empty Prompt
    print("\n==========================================")
    print(" TEST 4: Invalid empty command error handling test")
    print("==========================================")
    try:
        generate_plan(command="")
        print("[ERROR] Test 4 Failed: Expected PlannerError was not raised")
    except PlannerError as pe:
        print(f"[OK] Test 4 PASSED: Handled empty input safely with PlannerError: '{pe}'")


if __name__ == "__main__":
    main()
