"""
Definicje Wiadomości Kontrolera Regis (Messages).

Katalog wszystkich silnie typowanych paczek danych przesyłanych przez agnostyczną magistralę MessageBus.
"""
from dataclasses import dataclass
from typing import Any


# =============================================================================
# 1. INTENCJE WEJŚCIOWE UŻYTKOWNIKA I PRZEPŁYW (USER INPUT & FLOW)
# =============================================================================

@dataclass(frozen=True)
class RawTextReceived:
    """Paczka surowych danych dla wiadomości tekstowej od użytkownika."""
    text: str
    sender: str


@dataclass(frozen=True)
class RawAudioReceived:
    """Paczka surowych danych audio od użytkownika (przed transkrypcją STT)."""
    audio_bytes: bytes
    sender: str


@dataclass(frozen=True)
class UserSpoke:
    """Gotowy, znormalizowany tekst wypowiedziany przez użytkownika (po przejściu przez STT lub z czystego tekstu)."""
    text: str
    sender: str


@dataclass(frozen=True)
class AgentSpoke:
    """Paczka zdarzenia: Agent wygenerował tekst (myśl lub odpowiedź docelową) przeznaczony dla użytkownika."""
    text: str
    sender: str


# =============================================================================
# 2. KOMENDY STERUJĄCE I AKCJE (SYSTEM CONTROL COMMANDS)
# =============================================================================

@dataclass(frozen=True)
class PlayAudioMessage:
    """Komenda do Satelity nakazująca odtworzenie wygenerowanego audio TTS."""
    client_id: str
    audio_b64: str


@dataclass(frozen=True)
class PauseSatelliteMessage:
    """Komenda do Satelity nakazująca wstrzymanie nasłuchiwania (np. w trakcie odtwarzania TTS)."""
    client_id: str


@dataclass(frozen=True)
class ResumeSatelliteMessage:
    """Komenda do Satelity nakazująca wznowienie nasłuchiwania."""
    client_id: str


@dataclass(frozen=True)
class ClearHistoryMessage:
    """Wiadomość systemowa o zresetowaniu historii konwersacji."""
    satellite_id: str | None = None


# =============================================================================
# 3. ZDARZENIA SIECIOWE I CYKL ŻYCIA KLIENTÓW (CLIENT LIFECYCLE & NETWORK)
# =============================================================================

@dataclass(frozen=True)
class ClientRegisteredMessage:
    """Paczka zdarzenia o zarejestrowaniu nowej Satelity lub Usługi."""
    client_id: str
    client_type: str
    room: str | None = None
    name: str | None = None


@dataclass(frozen=True)
class ClientUnregisteredMessage:
    """Paczka zdarzenia o wyrejestrowaniu / rozłączeniu Satelity."""
    client_id: str


@dataclass(frozen=True)
class ClientUpdatedMessage:
    """Paczka zdarzenia: aktualizacja profilu / konfiguracji klienta."""
    client_id: str
    client: dict


@dataclass(frozen=True)
class ClientCommandResultMessage:
    """Paczka zdarzenia: rezultat wykonania komendy przez klienta WebSocket."""
    client_id: str
    command: str
    success: bool
    error: str | None = None
    result: dict | None = None


@dataclass(frozen=True)
class SatelliteEventMessage:
    """Paczka zdarzenia: satelita zgłasza zmianę swojego stanu, np. nasłuchuje, przetwarza."""
    satellite_id: str
    event_type: str
    data: dict


# =============================================================================
# 4. TELEMETRIA I MONITORING NA ŻYWO (DASHBOARD TELEMETRY & LOGS)
# =============================================================================

@dataclass(frozen=True)
class ConversationTurnMessage:
    """Paczka zdarzenia o zakończonej turze konwersacji (z metrykami latencji i narzędziami)."""
    satellite_id: str
    user_text: str
    assistant_text: str
    worker_id: str
    room: str | None = None
    tools: list[dict] | None = None
    elapsed_ms: int | None = None
    profiler: dict | None = None
    model: str = "unknown"


@dataclass(frozen=True)
class SystemLogMessage:
    """Paczka zdarzenia logu systemowego dla konsoli na żywo."""
    level: str
    message: str
    source: str = "controller"


@dataclass(frozen=True)
class AgentActionMessage:
    """Paczka zdarzenia oznaczająca aktywność narzędzia (start lub koniec)."""
    satellite_id: str
    action_type: str  # np. 'tool_call' lub 'tool_result'
    tool_name: str
    tool_args: dict | None = None
    tool_result: str | None = None

