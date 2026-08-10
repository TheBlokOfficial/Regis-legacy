import pytest


@pytest.mark.anyio
async def test_status_snapshot_uses_current_provider_registry_contract():
    """Dashboard nie może zależeć od nazw API usuniętych w refaktoryzacji providerów."""
    from controller.endpoints.system import get_status_snapshot

    snapshot = await get_status_snapshot()

    assert "controller" in snapshot
    assert {"llm_count", "stt_count", "tts_count", "full_mode"} <= snapshot["controller"].keys()
