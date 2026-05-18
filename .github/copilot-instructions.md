# qToggleServer – Copilot Instructions

## Commands

```bash
uv sync --extra opt          # install all deps including optional (postgres, mongo, redis)
uv run pytest                # run all tests
uv run pytest tests/unit/qtoggleserver/core/test_ports.py::test_name   # single test
ruff check qtoggleserver     # lint
ruff format qtoggleserver    # format
```

Pre-commit hooks run `ruff check` and `ruff format` automatically.

## Architecture

qToggleServer is a [qToggle protocol](https://github.com/qtoggle/docs) server. The main concepts:

- **Ports** (`qtoggleserver/core/ports.py`) — the central abstraction. A port has a boolean or number value and a set of attributes. `BasePort` is the base class; hardware drivers subclass it.
- **Peripherals** (`qtoggleserver/peripherals/`) — hardware devices that own one or more ports. Subclass `Peripheral` and implement `make_port_args()` to declare ports. Peripherals may run blocking I/O in a `ThreadedRunner`.
- **Device** (`qtoggleserver/core/device/`) — represents the local device. Attributes are module-level variables in `device/attrs.py`; `device/__init__.py` loads/saves/resets them via `persist`.
- **Slaves** (`qtoggleserver/slaves/`) — remote qToggle devices proxied over HTTP. Master discovers and manages slave ports alongside local ports.
- **Expressions** (`qtoggleserver/core/expressions/`) — expression language evaluated per-port. Ports can have `expression`, `transform_read`, and `transform_write` fields.
- **Events / Webhooks** (`qtoggleserver/core/events/`, `qtoggleserver/core/webhooks.py`) — internal event bus; webhooks deliver events to external URLs.
- **Persistence** (`qtoggleserver/persist/`) — async, pluggable storage. Drivers: JSON (default), MongoDB, PostgreSQL, Redis. Never access a driver directly; use `persist.query/insert/update/remove/get_value/set_value`.
- **Web layer** (`qtoggleserver/web/`) — Tornado HTTP server. API handlers live in `qtoggleserver/core/api/funcs/`.
- **Config** (`qtoggleserver/conf/`) — HOCON format (pyhocon). Settings accessed as `settings.<section>.<key>`.

## Key Conventions

### Attribute resolution on ports
`get_attr(name)` resolves in this order:
1. `attr_get_<name>()` / `attr_is_<name>()` method on the port class
2. `_<name>` instance variable
3. `attr_get_default_<name>()` / `attr_is_default_<name>()` method
4. Returns `None` (attribute unsupported)

To handle attribute writes, implement `attr_set_<name>(value)`. Declare custom attributes in the `ADDITIONAL_ATTRDEFS` class dict.

### `core_ports.get_all()` returns a `ValuesView`
Always wrap it with `list()` before iterating across `await` points or during mutations:
```python
for port in list(core_ports.get_all()):
    await port.some_async_method()
```

### Dynamic class loading
Classes are referenced by dotted Python path in config and are loaded at runtime via `dynload_utils.load_attr("module.path.ClassName")`.

### Async throughout
Everything is `async`/`await` on a single Tornado event loop. Blocking I/O must be offloaded to `ThreadedRunner` (used by `Peripheral` subclasses).

### Type annotations
All production code requires type annotations (ruff `ANN` rules). `*args`, `**kwargs`, and `Any` return types are exempt. Line length is 120 characters.

### Tests
- `tests/unit/` and `tests/integration/`, run via `pytest` with `asyncio_mode = "auto"` (no `@pytest.mark.asyncio` needed).
- Use `MockPersistDriver`, `MockBooleanPort`/`MockNumberPort`, and `MockPeripheral` from `tests/unit/qtoggleserver/mock/` in fixtures.
- Mock `asyncio.Lock` with `mocker.patch("asyncio.Lock")` when creating ports outside the running event loop.
- `tests/conftest.py` provides common fixtures (`mock_persist_driver`, `mock_num_port1`, etc.).

## Expression Language

Expressions are strings assigned to port `expression`, `transform_read`, or `transform_write` attributes. They are parsed by `qtoggleserver/core/expressions/__init__.py:parse()` and evaluated each core loop iteration.

**Syntax forms:**
| Prefix | Example | Meaning |
|--------|---------|---------|
| `$port_id` | `$sensor1` | value of port `sensor1` |
| `$port_id:attr` | `$sensor1:enabled` | attribute `enabled` of port `sensor1` |
| `$:attr` | `$:enabled` | attribute of *this* port (self-reference) |
| `@port_id` | `@sensor1` | previous value of port `sensor1` (write context) |
| `#:attr` | `#:name` | attribute of the local device |
| `#slave_name:attr` | `#hub:name` | attribute of a slave device |
| `func(...)` | `ADD($a, $b)` | function call |
| literal | `42`, `true`, `"hi"` | literal value |

**Roles** (`Role` enum in `base.py`): `VALUE`, `TRANSFORM_READ`, `TRANSFORM_WRITE`, `FILTER`. Port references to other ports are only allowed in `VALUE` role; `TRANSFORM_READ`/`TRANSFORM_WRITE` may only reference the port itself.

**Time dependencies** (`DEP_SECOND`, `DEP_MINUTE`, `DEP_HOUR`, `DEP_DAY`, `DEP_MONTH`, `DEP_YEAR`, `DEP_ASAP`): expressions declare which time units they depend on via `get_deps()`. The core loop re-evaluates expressions only when a relevant dep has changed.

**Implementing a new function:**
```python
from qtoggleserver.core.expressions.functions import Function, function
from qtoggleserver.core.expressions.base import EvalContext, EvalResult, Role

@function("MY_FUNC")
class MyFunc(Function):
    MIN_ARGS = 2
    MAX_ARGS = 2
    DEPS = set()           # add DEP_* constants if time-sensitive
    TRANSFORM_OK = True    # set False to disallow in transform expressions

    async def _eval(self, context: EvalContext) -> EvalResult:
        args = await self.eval_args(context)
        return args[0] + args[1]
```

The `@function("NAME")` decorator registers the class in the global `FUNCTIONS` dict. `EvalResult` is `int | float | str`.

## Master / Slave Architecture

A *master* qToggleServer device can proxy one or more *slave* qToggle devices over HTTP.

**`Slave`** (`slaves/devices.py`) — represents a remote device. Key fields:
- `_scheme`, `_host`, `_port`, `_path` — HTTP endpoint
- `_poll_interval` — seconds between polling cycles (0 = use listen mode only)
- `_listen_enabled` — whether to open a persistent listen session to receive push events
- `_provisioning_attrs` — attribute names changed while the slave was offline, to be pushed when it comes back online

**Sync modes:** A slave stays in sync via two complementary mechanisms that can be combined:
1. **Polling** — master periodically GETs the slave's ports and device attrs.
2. **Listen** — master holds an open HTTP request; the slave pushes events (value changes, attribute changes) as they happen.

**Discovery** (`slaves/discover/`) — enabled when a WiFi AP interface is available (`discover.is_enabled()`). The master acts as a WiFi AP; unconfigured slave devices connect to it. The master probes the DHCP client list, connects to each new IP, reads device attributes, and stores the result as a `DiscoveredDevice`. The UI then lets the user confirm and add the device as a slave.

**`SlavePort`** (`slaves/ports.py`) — subclass of `BasePort` that proxies a remote port. Its `read_value()` / `write_value()` forward over HTTP to the slave via the `Slave._parallel_api_caller` (throttled to `_MAX_PARALLEL_API_CALLS = 2` concurrent calls). Slave port IDs are prefixed with the slave name: `slave_name.port_id`.

**Provisioning** — when a slave reconnects after being offline, the master replays any attribute changes or webhook/reverse-API configuration that were queued in `_provisioning_attrs`, `_provisioning_webhooks`, `_provisioning_reverse`.

## API Handler Conventions

The web layer is Tornado. Handlers live in `qtoggleserver/web/handlers.py`; business logic lives in `qtoggleserver/core/api/funcs/` (and per-subsystem `api/funcs/` files).

**Defining an API function:**
```python
from qtoggleserver.core import api as core_api

@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)   # or NORMAL / VIEWONLY / NONE
async def get_something(request: core_api.APIRequest) -> dict:
    ...
    return {"key": "value"}
```

- The decorator enforces the minimum access level; raises `APIError(401, "authentication-required")` or `APIError(403, "forbidden")` automatically.
- The function receives an `APIRequest` wrapping the Tornado handler. Useful properties: `request.access_level`, `request.username`, `request.query` (dict), `request.body` (bytes), `request.headers`.
- Return value is JSON-serialised and sent as the response body.
- Raise `core_api.APIError(status, "error-code", **extra_params)` to return an error. The `error-code` and any extra kwargs become the JSON response.
- Raise `core_api.APIAccepted(response)` to return HTTP 202 with an optional body.

**Registering a handler** — add a Tornado `URLSpec` entry in `web/server.py` and wire it to a `web/handlers.py` class that calls `self.call_api_func(func_module.func_name)`.

**Access levels:** `ACCESS_LEVEL_NONE=0`, `ACCESS_LEVEL_VIEWONLY=10`, `ACCESS_LEVEL_NORMAL=20`, `ACCESS_LEVEL_ADMIN=30`.

**Input validation** — use `core_api_schema.validate(data, json_schema, ...)` (wraps `jsonschema`). Pass `unexpected_field_code` to customise the error code for unrecognised fields.
