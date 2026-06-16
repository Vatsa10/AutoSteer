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
            file_ids = list(payload.get("file_ids") or [])
            preferences = payload.get("preferences")
            # Process inline files
            inline_files = payload.get("files")
            if inline_files:
                import base64 as _b64
                from src.integrations.files import save_upload
                for f in inline_files:
                    try:
                        raw = _b64.b64decode(f["content"])
                        if len(raw) <= 5 * 1024 * 1024:
                            meta = save_upload(f["filename"], raw)
                            file_ids.append(meta["file_id"])
                    except Exception as exc:
                        print(f"[ws] inline file error: {exc}")

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
                        file_ids=file_ids,
                        preferences=preferences,
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
