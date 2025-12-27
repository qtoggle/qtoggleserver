import pytest

from qtoggleserver.conf import metadata


class TestGet:
    def test_existing_key(self):
        """Should return the value associated with the key from the metadata entries."""

        metadata._metadata_entries = {"test_key": "test_value", "another_key": 123}

        result = metadata.get("test_key")

        assert result == "test_value"

    def test_nonexistent_key_default_none(self):
        """Should return None when the key does not exist and no default is provided."""

        metadata._metadata_entries = {"test_key": "test_value"}

        result = metadata.get("nonexistent_key")

        assert result is None

    def test_nonexistent_key_with_default(self):
        """Should return the provided default value when the key does not exist."""

        metadata._metadata_entries = {"test_key": "test_value"}

        result = metadata.get("nonexistent_key", "default_value")

        assert result == "default_value"

    def test_empty_metadata(self):
        """Should return `None` when metadata entries are empty and no default is provided."""

        metadata._metadata_entries = {}

        result = metadata.get("any_key")

        assert result is None


class TestGetAll:
    def test_all_entries(self):
        """Should return all entries present in the metadata catalog."""

        entries = {"test_key": "test_value", "another_key": 123}
        metadata._metadata_entries = entries
        result = metadata.get_all()
        assert result == entries

    def test_clone(self):
        """Should return a *copy* of the entries."""

        metadata._metadata_entries = {"test_key": "test_value", "another_key": 123}
        result = metadata.get_all()
        result["yet_another_key"] = 234

        assert "yet_another_key" not in metadata._metadata_entries


class TestLoadMetadata:
    async def test_with_value(self, mocker):
        """Should load metadata with a direct value parameter."""

        metadata._metadata_entries = {}
        spy_logger = mocker.patch("qtoggleserver.conf.metadata.logger")

        await metadata.load_metadata({"name": "test_meta", "value": "test_value"})

        assert metadata._metadata_entries["test_meta"] == "test_value"
        spy_logger.debug.assert_called_once_with("loaded metadata %s = %s", "test_meta", '"test_value"')

    async def test_with_value_complex(self, mocker):
        """Should load metadata with a complex value (dict)."""

        metadata._metadata_entries = {}
        mocker.patch("qtoggleserver.conf.metadata.logger")
        complex_value = {"nested": {"key": "value"}, "list": [1, 2, 3]}

        await metadata.load_metadata({"name": "test_meta", "value": complex_value})

        assert metadata._metadata_entries["test_meta"] == complex_value

    async def test_with_cmd(self, mocker):
        """Should call run_get_cmd with the cmd parameter and load the returned value."""

        metadata._metadata_entries = {}
        mocker.patch("qtoggleserver.conf.metadata.logger")
        spy_run_get_cmd = mocker.patch("qtoggleserver.conf.metadata.run_get_cmd", return_value={"value": "cmd_result"})

        await metadata.load_metadata({"name": "test_meta", "cmd": "echo test"})

        spy_run_get_cmd.assert_called_once_with("echo test", "metadata test_meta", required_fields=["value"])
        assert metadata._metadata_entries["test_meta"] == "cmd_result"

    async def test_with_sensitive_value(self, mocker):
        """Should not log the value when sensitive parameter is True."""

        metadata._metadata_entries = {}
        spy_logger = mocker.patch("qtoggleserver.conf.metadata.logger")

        await metadata.load_metadata({"name": "secret_meta", "value": "secret_value", "sensitive": True})

        assert metadata._metadata_entries["secret_meta"] == "secret_value"
        spy_logger.debug.assert_called_once_with("loaded metadata %s", "secret_meta")

    async def test_missing_name(self):
        """Should raise ValueError when the name parameter is missing."""

        with pytest.raises(ValueError, match="Missing 'name' parameter"):
            await metadata.load_metadata({"value": "test_value"})

    async def test_missing_value_and_cmd(self):
        """Should raise ValueError when both value and cmd parameters are missing."""

        with pytest.raises(ValueError, match="Missing 'value' or 'cmd' parameter"):
            await metadata.load_metadata({"name": "test_meta"})

    async def test_value_priority_over_cmd(self, mocker):
        """Should use the value parameter when both value and cmd are provided."""

        metadata._metadata_entries = {}
        mocker.patch("qtoggleserver.conf.metadata.logger")
        spy_run_get_cmd = mocker.patch("qtoggleserver.conf.metadata.run_get_cmd")

        await metadata.load_metadata({"name": "test_meta", "value": "direct_value", "cmd": "echo test"})

        spy_run_get_cmd.assert_not_called()
        assert metadata._metadata_entries["test_meta"] == "direct_value"


class TestInit:
    async def test_multiple_metadata(self, mocker):
        """Should load metadata entries from settings."""

        metadata._metadata_entries = {}
        settings_metadata = [
            {"name": "meta1", "value": "value1"},
            {"name": "meta2", "value": "value2"},
            {"name": "meta3", "value": "value3"},
        ]
        mocker.patch("qtoggleserver.conf.metadata.settings.metadata", settings_metadata)
        spy_load_metadata = mocker.patch("qtoggleserver.conf.metadata.load_metadata")

        await metadata.init()

        assert spy_load_metadata.call_count == 3
        spy_load_metadata.assert_any_call({"name": "meta1", "value": "value1"})
        spy_load_metadata.assert_any_call({"name": "meta2", "value": "value2"})
        spy_load_metadata.assert_any_call({"name": "meta3", "value": "value3"})

    async def test_exception_handling(self, mocker):
        """Should log an error and continue when load_metadata raises an exception."""

        metadata._metadata_entries = {}
        settings_metadata = [
            {"name": "meta1", "value": "value1"},
            {"name": "meta2", "value": "value2"},
        ]
        mocker.patch("qtoggleserver.conf.metadata.settings.metadata", settings_metadata)
        spy_logger = mocker.patch("qtoggleserver.conf.metadata.logger")

        async def mock_load_metadata(params):
            if params["name"] == "meta1":
                raise ValueError("Test error")

        mocker.patch("qtoggleserver.conf.metadata.load_metadata", side_effect=mock_load_metadata)

        await metadata.init()

        spy_logger.error.assert_called_once()
        assert "failed to load metadata from params" in spy_logger.error.call_args[0][0]

    async def test_all_fail_continues(self, mocker):
        """Should continue processing even if all metadata entries fail to load."""

        metadata._metadata_entries = {}
        settings_metadata = [
            {"name": "meta1", "value": "value1"},
            {"name": "meta2", "value": "value2"},
        ]
        mocker.patch("qtoggleserver.conf.metadata.settings.metadata", settings_metadata)
        spy_logger = mocker.patch("qtoggleserver.conf.metadata.logger")
        mocker.patch("qtoggleserver.conf.metadata.load_metadata", side_effect=ValueError("Test error"))

        await metadata.init()

        assert spy_logger.error.call_count == 2
