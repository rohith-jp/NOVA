import contextlib
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.executor import PlanActVerifyExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])
executor = PlanActVerifyExecutor()


@router.websocket("/connect")
async def websocket_connect(websocket: WebSocket) -> None:
    """General WebSocket connection endpoint."""
    await websocket.accept()
    await websocket.send_json(
        {
            "type": "connected",
            "message": "NOVA WebSocket server connected.",
        }
    )
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        pass


@router.websocket("/stream")
async def websocket_agent_stream(websocket: WebSocket) -> None:
    """Agent Live Event Stream WebSocket Endpoint.

    Clients send JSON:
        {"command": "Search for Next.js 15 features", "context": "optional context"}

    Server streams live execution events:
        - PLAN: Plan decomposition (summary, steps)
        - TOOL_CALL: Tool invocation
        - EVIDENCE: Action output data
        - DECISION: Step verification pass/fail
        - SUCCESS: Overall plan completion
        - ERROR: Safe error notification
    """
    await websocket.accept()
    await websocket.send_json(
        {
            "event": "CONNECTED",
            "message": "Connected to NOVA Agent Event Stream",
        }
    )

    try:
        while True:
            raw_text = await websocket.receive_text()
            try:
                payload = json.loads(raw_text)
            except Exception:
                await websocket.send_json(
                    {
                        "event": "ERROR",
                        "data": {"error": "Invalid JSON format received."},
                    }
                )
                continue

            command = payload.get("command", "")
            context = payload.get("context", None)

            if not command or not command.strip():
                await websocket.send_json(
                    {
                        "event": "ERROR",
                        "data": {"error": "Command field is required and cannot be empty."},
                    }
                )
                continue

            logger.info(f"[WS STREAM] Received command: '{command}'")

            # Stream execution events
            async for event in executor.execute_command_stream(command=command, context=context):
                await websocket.send_json(event)

    except WebSocketDisconnect:
        logger.info("[WS STREAM] Client disconnected.")
    except Exception as e:
        logger.error(f"[WS STREAM] Unexpected error: {e}")
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {
                    "event": "ERROR",
                    "data": {"error": f"Internal stream error: {str(e)}"},
                }
            )
