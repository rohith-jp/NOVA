import sys
from app.services.gemini import generate_response


def test_gemini_integration():
    print("=== Testing Gemini API Integration ===")
    test_prompt = (
        "Say 'Hello from NOVA AI Assistant!' and confirm you are online in one concise sentence."
    )
    print(f"Sending test command: '{test_prompt}'\n")

    try:
        response = generate_response(test_prompt)
        print("Received response from Gemini:")
        print(f"-> {response}\n")

        assert len(response) > 0, "Response should not be empty"
        print("[OK] Gemini integration test PASSED!")

    except Exception as e:
        print(f"[ERROR] Gemini integration test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    test_gemini_integration()
