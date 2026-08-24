from fastapi.testclient import TestClient
from app.main import app


def test_websocket_streaming():
    print("=== Testing FastAPI WebSocket Event Stream (/ws/stream) ===")
    client = TestClient(app)

    with client.websocket_connect("/ws/stream") as websocket:
        # 1. First event should be CONNECTED
        init_event = websocket.receive_json()
        print(f"[WS RX] Initial Event: {init_event}")
        assert init_event["event"] == "CONNECTED"

        # 2. Send command to trigger agent execution stream
        cmd_payload = {"command": "Search for Next.js 15 features and summarize"}
        print(f"[WS TX] Sending Command: {cmd_payload}")
        websocket.send_json(cmd_payload)

        events_received = []
        while True:
            evt = websocket.receive_json()
            event_type = evt.get("event")
            events_received.append(event_type)
            print(f"[WS RX] Event [{event_type}]: {evt.get('data')}")

            # Verify no hidden chain of thought is present in data payload
            data_str = str(evt.get("data", {}))
            assert "chain_of_thought" not in data_str
            assert "raw_prompt" not in data_str

            if event_type in ("SUCCESS", "ERROR"):
                break

        print(f"\n[OK] Received Event Sequence: {events_received}")
        assert "PLAN" in events_received
        assert "TOOL_CALL" in events_received
        assert "EVIDENCE" in events_received
        assert "DECISION" in events_received
        assert "SUCCESS" in events_received
        print("[OK] WebSocket Agent Event Streaming test PASSED!")


if __name__ == "__main__":
    test_websocket_streaming()
