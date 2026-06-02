import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.database import get_session_factory

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    factory = get_session_factory()
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            message = payload.get("message", "")
            conversation_id = payload.get("conversation_id")

            engine = websocket.app.state.engine
            if engine:
                async with factory() as session:
                    result = await engine.process_message(
                        user_message=message,
                        conversation_id=conversation_id,
                        session=session,
                    )
                await websocket.send_json(result)
            else:
                await websocket.send_json({"error": "Engine not initialized"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
