import asyncio

from qtoggleserver.core.device import attrs as device_attrs
from qtoggleserver.core.device import events as device_events


async def test_attrs_update_loop_triggers_device_update_event(mocker):
    """Should trigger a device-update event once per ATTRS_UPDATE_INTERVAL seconds."""

    # Use a short interval so the test runs fast
    mocker.patch.object(device_attrs, "ATTRS_UPDATE_INTERVAL", 0.05)

    expected_calls = 3
    all_called = asyncio.Event()
    call_count = 0

    async def _mock_trigger_update() -> None:
        nonlocal call_count
        call_count += 1
        if call_count >= expected_calls:
            all_called.set()

    mocker.patch.object(device_events, "trigger_update", side_effect=_mock_trigger_update)

    await device_attrs.init()
    try:
        await asyncio.wait_for(all_called.wait(), timeout=1.0)
    finally:
        await device_attrs.cleanup()

    assert call_count >= expected_calls
