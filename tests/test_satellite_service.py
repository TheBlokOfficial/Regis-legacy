"""
Testy jednostkowe dla parsowania poleceń w usłudze Satelity.
"""
from unittest.mock import MagicMock
from protocol.schemas import SatelliteAction
from client.services.satellite.__main__ import SatelliteService


def test_handle_satellite_control_flat_and_nested_payload():
    service = SatelliteService.__new__(SatelliteService)
    service.event_bus = MagicMock()
    service.state = "READY"
    service._start_wakeword_listening = MagicMock()

    # 1. Płaski payload {"action": "resume"}
    service._paused = True
    service._handle_satellite_control({"action": "resume"})
    assert service._paused is False
    service._start_wakeword_listening.assert_called_once()

    # Reset
    service._start_wakeword_listening.reset_mock()

    # 2. Zagnieżdżony payload {"data": {"action": "resume"}}
    service._paused = True
    service._handle_satellite_control({"data": {"action": "resume"}})
    assert service._paused is False
    service._start_wakeword_listening.assert_called_once()

    # 3. Polecenie PAUSE
    service._handle_satellite_control({"data": {"action": "pause"}})
    assert service._paused is True
