"""
Zarządzanie historią aktywnych sesji konwersacji w pamięci Kontrolera.

Architektura oparta na OOP (Object-Oriented Programming).
Stan utrzymywany jest w izolowanych obiektach `ConversationSession`.
Identyfikacja fizyczna (satellite_id) mapowana jest na wirtualne session_id.
"""
import time
import uuid
import datetime

class ConversationSession:
    """Reprezentuje pojedynczą sesję konwersacji."""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.history: list[dict] = []
        self.last_interaction: float = time.time()
        self.history_limit: int = 12

    def append_message(self, role: str, content: str, **kwargs) -> None:
        """Dodaje wiadomość do historii i weryfikuje limity."""
        now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": now,
            **kwargs
        })
        self.last_interaction = time.time()
        
        if len(self.history) > self.history_limit:
            del self.history[:-self.history_limit]

    def get_history(self) -> list[dict]:
        """Zwraca kopię (lub referencję) listy wiadomości."""
        return self.history
        
    def clear(self) -> None:
        """Czyści całkowicie historię tej sesji."""
        self.history.clear()


# Mapowanie: satellite_id -> session_id
client_to_session: dict[str, str] = {}

# Słownik aktywnych instancji sesji
active_sessions: dict[str, ConversationSession] = {}


def get_session_for_client(satellite_id: str | None, create_if_missing: bool = True) -> ConversationSession | None:
    """Pobiera lub (jeśli create_if_missing=True) tworzy obiekt sesji dla danego sprzętu."""
    sid = satellite_id or "default"
    
    # 1. Sprawdź, czy klient ma przypisane session_id
    if sid not in client_to_session:
        if not create_if_missing:
            return None
        client_to_session[sid] = f"session_{uuid.uuid4().hex[:8]}"
        
    session_id = client_to_session[sid]
    
    # 2. Sprawdź, czy instancja sesji istnieje
    if session_id not in active_sessions:
        if not create_if_missing:
            return None
        active_sessions[session_id] = ConversationSession(session_id)
        
    return active_sessions[session_id]

def clear_all_sessions() -> None:
    """Opcjonalna metoda do globalnego restartu pamięci."""
    active_sessions.clear()
    client_to_session.clear()
