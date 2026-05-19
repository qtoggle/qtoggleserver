import asyncio

import pytest

from qtoggleserver.conf import settings
from qtoggleserver.core import main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.events import handlers as event_handlers
from tests.unit.qtoggleserver.mock.ports import MockNumberPort


@pytest.fixture
def with_attr_change_handler():
    """Register the main module's attr-change event handler for the duration of the test."""
    event_handlers._registered_handlers.append(main._attr_change_handler)
    main._attr_change_handler._pending.clear()
    yield
    if main._attr_change_handler in event_handlers._registered_handlers:
        event_handlers._registered_handlers.remove(main._attr_change_handler)
    main._attr_change_handler._pending.clear()


async def test_eval_trigger_set_expression(mock_num_port1, mock_num_port2, mocker):
    """Should trigger expression evaluation and write resulting value when setting an expression to a port."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    await mock_num_port2.set_attr("expression", "MUL($nid1, 10)")
    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port2.transform_and_write_value.assert_called_once_with(40)


async def test_eval_trigger_value_change(mock_num_port1, mock_num_port2, mocker):
    """Should trigger expression evaluation and write resulting value when a dependent port's value changes."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("MUL($nid1, 10)")
    mock_num_port1.set_next_value(6)

    mocker.patch.object(mock_num_port2, "transform_and_write_value")
    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port2.transform_and_write_value.assert_called_once_with(60)


async def test_eval_trigger_value_change_own(mock_num_port1, mock_num_port2, mocker):
    """Should trigger expression evaluation and write resulting value when own port value changes, as a regular dep."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("MUL($nid1, $nid2)")
    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port2.transform_and_write_value.assert_called_once_with(30)


async def test_eval_trigger_ignore_inexistent_port(mock_num_port1, mock_num_port2, mocker):
    """Should not trigger expression evaluation when expression includes an inexistent port."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port2.set_last_read_value(5)
    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("MUL($nid1, $inexistent)")
    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port2.transform_and_write_value.assert_not_called()


async def test_eval_trigger_port_enabled(mock_num_port1, mocker):
    """Should trigger expression evaluation and write resulting value when port becomes enabled."""

    mock_num_port1.set_last_read_value(4)
    mock_num_port1.set_writable(True)
    mock_num_port1.set_expression("MUL($, 10)")
    mock_num_port1.set_next_value(6)
    mocker.patch.object(mock_num_port1, "transform_and_write_value")

    await mock_num_port1.disable()
    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port1.transform_and_write_value.assert_not_called()

    await mock_num_port1.enable()
    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port1.transform_and_write_value.assert_called_once_with(60)


async def test_eval_trigger_port_attr_change(mock_num_port1, mock_num_port2, with_attr_change_handler, mocker):
    """Should trigger expression evaluation when a port's attribute changes."""

    mock_num_port2.set_writable(True)
    mock_num_port2.set_expression("$nid1:enabled")
    mocker.patch.object(mock_num_port2, "transform_and_write_value")

    # Changing port1's display_name fires a debounced PortUpdate event
    await mock_num_port1.set_attr("display_name", "updated")
    # Wait for the debounced _after_set_attr task to run and dispatch the PortUpdate event
    await asyncio.sleep(settings.core.tick_interval / 1000)

    await main.read_ports()
    await asyncio.sleep(settings.core.tick_interval / 1000)
    mock_num_port2.transform_and_write_value.assert_called_once_with(1)


async def test_eval_trigger_port_add(mock_num_port1, with_attr_change_handler, mocker):
    """Should trigger expression evaluation when a new port is added."""

    mock_num_port1.set_writable(True)
    mock_num_port1.set_last_read_value(0)
    # Expression depends on an attribute of nid3, which doesn't exist yet
    mock_num_port1.set_expression("$nid3:enabled")
    mocker.patch.object(mock_num_port1, "transform_and_write_value")

    # Loading the port fires a PortAdd event for nid3 → $nid3: added to pending attr-change deps
    nid3 = (await core_ports.load([{"driver": MockNumberPort, "port_id": "nid3", "value": None}]))[0]
    try:
        await nid3.enable()

        await main.read_ports()
        await asyncio.sleep(settings.core.tick_interval / 1000)
        mock_num_port1.transform_and_write_value.assert_called_once_with(1)
    finally:
        await nid3.remove(persisted_data=False)


async def test_eval_trigger_port_remove(mock_num_port1, with_attr_change_handler, mocker):
    """Should trigger expression evaluation when a port is removed."""

    # Load a temporary port that will be removed during the test
    nid3 = (await core_ports.load([{"driver": MockNumberPort, "port_id": "nid3", "value": None}]))[0]
    await nid3.enable()

    mock_num_port1.set_writable(True)
    # Expression depends on an attribute of nid3; removing nid3 must trigger re-evaluation
    mock_num_port1.set_expression("$nid3:enabled")
    spy = mocker.spy(mock_num_port1, "eval_and_push_write")

    # Removing the port fires a PortRemove event → $nid3: added to pending attr-change deps
    await nid3.remove(persisted_data=False)

    await main.read_ports()
    spy.assert_called_once()


async def test_eval_trigger_device_attr_change(mock_num_port1, with_attr_change_handler, mocker):
    """Should trigger expression evaluation when a device attribute changes."""

    from qtoggleserver.core.device import attrs as device_attrs
    from qtoggleserver.core.device import events as device_events

    original_display_name = device_attrs.display_name
    try:
        mock_num_port1.set_writable(True)
        mock_num_port1.set_last_read_value(0)
        # Expression depends on the device's display_name attribute
        mock_num_port1.set_expression("#:display_name")
        mocker.patch.object(mock_num_port1, "transform_and_write_value")

        # Set a non-empty display_name so the expression evaluates to 1 (truthy string → 1)
        device_attrs.display_name = "test"
        device_attrs.invalidate_attrs()
        # Fire the DeviceUpdate event (normally emitted by the device attrs update loop)
        await device_events.trigger_update()

        await main.read_ports()
        await asyncio.sleep(settings.core.tick_interval / 1000)
        mock_num_port1.transform_and_write_value.assert_called_once_with(1)
    finally:
        device_attrs.display_name = original_display_name
        device_attrs.invalidate_attrs()
