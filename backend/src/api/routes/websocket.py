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
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        dead: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for conn in dead:
            self.active_connections.remove(conn)


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
            target_agent = payload.get("target_agent")

            engine = websocket.app.state.engine
            if not engine:
                await websocket.send_json({"type": "error", "message": "Engine not initialized"})
                continue

            try:
                async with factory() as session:
                    async for event in engine.process_message_stream(
                        user_message=message,
                        conversation_id=conversation_id,
                        target_agent=target_agent,
                        session=session,
                    ):
                        await websocket.send_json(event)
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                if payload.get("type") == "broadcast":
                    await manager.broadcast(payload)
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
