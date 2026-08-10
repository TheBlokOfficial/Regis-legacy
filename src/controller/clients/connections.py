"""Transport WebSocket dla zarejestrowanych klientów Kontrolera."""
from fastapi import WebSocket

from protocol.schemas import WSCommand


class ClientConnectionManager:
    """Utrzymuje aktywne połączenia i wysyła komendy do klienta."""

    def __init__(self) -> None:
        self.active_connections: dict[str, WebSocket] = {}

    def is_connected(self, client_id: str) -> bool:
        return client_id in self.active_connections

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str) -> None:
        self.active_connections.pop(client_id, None)

    async def send_command(self, client_id: str, command: str, data: dict | None = None) -> bool:
        """Wysyła komendę przez WebSocket; False oznacza brak lub utratę połączenia."""
        websocket = self.active_connections.get(client_id)
        if websocket is None:
            return False
        try:
            payload = WSCommand(command=command, data=data or {})
            await websocket.send_text(payload.model_dump_json())
            return True
        except Exception:
            self.disconnect(client_id)
            return False


client_manager = ClientConnectionManager()
