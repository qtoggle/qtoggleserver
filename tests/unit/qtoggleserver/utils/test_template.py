from qtoggleserver.utils import template
from qtoggleserver.utils.template import get_env, get_native_env, make, make_native, render, render_async, render_native


class TestGetEnv:
    def test_create(self, mocker):
        """Should call Environment to create an environment and return it."""

        template._environment = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)

        env = get_env()

        spy_env.assert_called_once()
        assert env is mock_env

    def test_singleton(self, mocker):
        """Should not attempt to re-create the environment for subsequent calls."""

        template._environment = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)
        get_env()

        spy_env.reset_mock()
        env = get_env()

        spy_env.assert_not_called()
        assert env is mock_env


class TestGetNativeEnv:
    def test_create(self, mocker):
        """Should call NativeEnvironment to create an environment and return it."""

        template._native_environment = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)

        env = get_native_env()

        spy_env.assert_called_once()
        assert env is mock_env

    def test_singleton(self, mocker):
        """Should not attempt to re-create the environment for subsequent calls."""

        template._native_environment = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)
        get_native_env()

        spy_env.reset_mock()
        env = get_native_env()

        spy_env.assert_not_called()
        assert env is mock_env


def test_make(mocker):
    """Should obtain the environment using `get_env()` and call `from_string()` on it with the source, returning
    the result."""

    mock_env = mocker.Mock()
    spy_get_env = mocker.patch("qtoggleserver.utils.template.get_env", return_value=mock_env)

    tmpl = make("{{some_source}}")

    spy_get_env.assert_called_once()
    mock_env.from_string.assert_called_once_with("{{some_source}}")
    assert tmpl is mock_env.from_string()


def test_make_native(mocker):
    """Should obtain the native environment using `get_native_env()` and call `from_string()` on it with the source,
    returning the result."""

    mock_env = mocker.Mock()
    spy_get_native_env = mocker.patch("qtoggleserver.utils.template.get_native_env", return_value=mock_env)

    tmpl = make_native("{{some_source}}")

    spy_get_native_env.assert_called_once()
    mock_env.from_string.assert_called_once_with("{{some_source}}")
    assert tmpl is mock_env.from_string()


def test_render(mocker):
    """Should make a template using `make()` and render it with given context."""

    mock_tmpl = mocker.Mock()
    spy_make = mocker.patch("qtoggleserver.utils.template.make", return_value=mock_tmpl)

    result = render("{{some_source}}", {"some": "context"})

    spy_make.assert_called_once_with("{{some_source}}")
    mock_tmpl.render.assert_called_once_with({"some": "context"})
    assert result is mock_tmpl.render()


async def test_render_async(mocker):
    """Should make a template using `make()` and render it with given context, asynchronously."""

    mock_tmpl = mocker.AsyncMock()
    spy_make = mocker.patch("qtoggleserver.utils.template.make", return_value=mock_tmpl)

    result = await render_async("{{some_source}}", {"some": "context"})

    spy_make.assert_called_once_with("{{some_source}}")
    mock_tmpl.render_async.assert_called_once_with({"some": "context"})
    assert result is await mock_tmpl.render_async()


async def test_render_native(mocker):
    """Should make a template using `make_native()` and render it with given context, asynchronously."""

    mock_tmpl = mocker.AsyncMock()
    spy_make_native = mocker.patch("qtoggleserver.utils.template.make_native", return_value=mock_tmpl)

    result = await render_native("{{some_source}}", {"some": "context"})

    spy_make_native.assert_called_once_with("{{some_source}}")
    mock_tmpl.render_async.assert_called_once_with({"some": "context"})
    assert result is await mock_tmpl.render_async()
