from qtoggleserver.utils import template
from qtoggleserver.utils.template import (
    get_env,
    get_native_env,
    make,
    make_native,
    render,
    render_native,
    render_sync,
    render_sync_native,
)


class TestGetEnv:
    def test_create(self, mocker):
        """Should call Environment to create an async environment by default and return it."""

        template._env = None
        template._env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)

        env = get_env()

        spy_env.assert_called_once_with(enable_async=True)
        assert env is mock_env

    def test_create_sync_false(self, mocker):
        """Should call Environment to create an async environment and return it."""

        template._env = None
        template._env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)

        env = get_env(sync=False)

        spy_env.assert_called_once_with(enable_async=True)
        assert env is mock_env

    def test_create_sync_true(self, mocker):
        """Should call Environment to create a sync environment and return it."""

        template._env = None
        template._env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)

        env = get_env(sync=True)

        spy_env.assert_called_once_with(enable_async=False)
        assert env is mock_env

    def test_singleton(self, mocker):
        """Should not attempt to re-create the environment for subsequent calls."""

        template._env = None
        template._env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)
        get_env()

        spy_env.reset_mock()
        env = get_env()

        spy_env.assert_not_called()
        assert env is mock_env

    def test_singleton_sync(self, mocker):
        """Should not attempt to re-create the environment for subsequent calls."""

        template._env = None
        template._env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)
        get_env(sync=True)

        spy_env.reset_mock()
        env = get_env(sync=True)

        spy_env.assert_not_called()
        assert env is mock_env

    def test_singleton_sync_async(self, mocker):
        """Should create separate environments for subsequent sync and async calls."""

        template._env = None
        template._env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.Environment", return_value=mock_env)
        get_env(sync=True)

        spy_env.reset_mock()
        env = get_env(sync=False)

        spy_env.assert_called_once_with(enable_async=True)
        assert env is mock_env


class TestGetNativeEnv:
    def test_create(self, mocker):
        """Should call NativeEnvironment to create an async environment by default and return it."""

        template._native_env = None
        template._native_env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)

        env = get_native_env()

        spy_env.assert_called_once_with(enable_async=True)
        assert env is mock_env

    def test_create_sync_false(self, mocker):
        """Should call NativeEnvironment to create an async environment and return it."""

        template._native_env = None
        template._native_env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)

        env = get_native_env(sync=False)

        spy_env.assert_called_once_with(enable_async=True)
        assert env is mock_env

    def test_create_sync_true(self, mocker):
        """Should call NativeEnvironment to create a sync environment and return it."""

        template._native_env = None
        template._native_env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)

        env = get_native_env(sync=True)

        spy_env.assert_called_once_with(enable_async=False)
        assert env is mock_env

    def test_singleton(self, mocker):
        """Should not attempt to re-create the environment for subsequent calls."""

        template._native_env = None
        template._native_env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)
        get_native_env()

        spy_env.reset_mock()
        env = get_native_env()

        spy_env.assert_not_called()
        assert env is mock_env

    def test_singleton_sync(self, mocker):
        """Should not attempt to re-create the environment for subsequent calls."""

        template._native_env = None
        template._native_env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)
        get_native_env(sync=True)

        spy_env.reset_mock()
        env = get_native_env(sync=True)

        spy_env.assert_not_called()
        assert env is mock_env

    def test_singleton_sync_async(self, mocker):
        """Should create separate environments for subsequent sync and async calls."""

        template._native_env = None
        template._native_env_sync = None
        mock_env = mocker.Mock()
        spy_env = mocker.patch("qtoggleserver.utils.template.NativeEnvironment", return_value=mock_env)
        get_native_env(sync=True)

        spy_env.reset_mock()
        env = get_native_env(sync=False)

        spy_env.assert_called_once_with(enable_async=True)
        assert env is mock_env


class TestMake:
    def test_default(self, mocker):
        """Should obtain the environment using `get_env(False)` and call `from_string()` on it with the source,
        returning the resulted template."""

        mock_env = mocker.Mock()
        spy_get_env = mocker.patch("qtoggleserver.utils.template.get_env", return_value=mock_env)

        tmpl = make("{{some_source}}")

        spy_get_env.assert_called_once_with(False)
        mock_env.from_string.assert_called_once_with("{{some_source}}")
        assert tmpl is mock_env.from_string()

    def test_async(self, mocker):
        """Should obtain the environment using `get_env(False)` and call `from_string()` on it with the source,
        returning the resulted template."""

        mock_env = mocker.Mock()
        spy_get_env = mocker.patch("qtoggleserver.utils.template.get_env", return_value=mock_env)

        tmpl = make("{{some_source}}")

        spy_get_env.assert_called_once_with(False)
        mock_env.from_string.assert_called_once_with("{{some_source}}")
        assert tmpl is mock_env.from_string()

    def test_sync(self, mocker):
        """Should obtain the environment using `get_env(True)` and call `from_string()` on it with the source,
        returning the resulted template."""

        mock_env = mocker.Mock()
        spy_get_env = mocker.patch("qtoggleserver.utils.template.get_env", return_value=mock_env)

        tmpl = make("{{some_source}}", sync=True)

        spy_get_env.assert_called_once_with(True)
        mock_env.from_string.assert_called_once_with("{{some_source}}")
        assert tmpl is mock_env.from_string()


class TestMakeNative:
    def test_default(self, mocker):
        """Should obtain the environment using `get_native_env(False)` and call `from_string()` on it with the source,
        returning the resulted template."""

        mock_env = mocker.Mock()
        spy_get_native_env = mocker.patch("qtoggleserver.utils.template.get_native_env", return_value=mock_env)

        tmpl = make_native("{{some_source}}")

        spy_get_native_env.assert_called_once_with(False)
        mock_env.from_string.assert_called_once_with("{{some_source}}")
        assert tmpl is mock_env.from_string()

    def test_async(self, mocker):
        """Should obtain the environment using `get_native_env(False)` and call `from_string()` on it with the source,
        returning the resulted template."""

        mock_env = mocker.Mock()
        spy_get_native_env = mocker.patch("qtoggleserver.utils.template.get_native_env", return_value=mock_env)

        tmpl = make_native("{{some_source}}")

        spy_get_native_env.assert_called_once_with(False)
        mock_env.from_string.assert_called_once_with("{{some_source}}")
        assert tmpl is mock_env.from_string()

    def test_sync(self, mocker):
        """Should obtain the environment using `get_native_env(True)` and call `from_string()` on it with the source,
        returning the resulted template."""

        mock_env = mocker.Mock()
        spy_get_native_env = mocker.patch("qtoggleserver.utils.template.get_native_env", return_value=mock_env)

        tmpl = make_native("{{some_source}}", sync=True)

        spy_get_native_env.assert_called_once_with(True)
        mock_env.from_string.assert_called_once_with("{{some_source}}")
        assert tmpl is mock_env.from_string()


async def test_render(mocker):
    """Should make a template using `make()` and render it with given context, asynchronously."""

    mock_tmpl = mocker.AsyncMock()
    spy_make = mocker.patch("qtoggleserver.utils.template.make", return_value=mock_tmpl)

    result = await render("{{some_source}}", {"some": "context"})

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


def test_render_sync(mocker):
    """Should make a template using `make()` and render it with given context."""

    mock_tmpl = mocker.Mock()
    spy_make = mocker.patch("qtoggleserver.utils.template.make", return_value=mock_tmpl)

    result = render_sync("{{some_source}}", {"some": "context"})

    spy_make.assert_called_once_with("{{some_source}}", sync=True)
    mock_tmpl.render.assert_called_once_with({"some": "context"})
    assert result is mock_tmpl.render()


def test_render_sync_native(mocker):
    """Should make a template using `make_native()` and render it with given context."""

    mock_tmpl = mocker.Mock()
    spy_make = mocker.patch("qtoggleserver.utils.template.make_native", return_value=mock_tmpl)

    result = render_sync_native("{{some_source}}", {"some": "context"})

    spy_make.assert_called_once_with("{{some_source}}", sync=True)
    mock_tmpl.render.assert_called_once_with({"some": "context"})
    assert result is mock_tmpl.render()
