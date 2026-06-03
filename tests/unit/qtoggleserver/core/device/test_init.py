from qtoggleserver.core import device


class TestGetPrettyName:
    def test_uses_display_name_when_available(self, mocker):
        """Should prefer display name over internal name."""

        mocker.patch("qtoggleserver.core.device.device_attrs.display_name", "My Device")
        mocker.patch("qtoggleserver.core.device.device_attrs.name", "device-1")

        assert device.get_pretty_name() == "My Device"

    def test_falls_back_to_name_when_display_name_missing(self, mocker):
        """Should fall back to name when display name is empty."""

        mocker.patch("qtoggleserver.core.device.device_attrs.display_name", "")
        mocker.patch("qtoggleserver.core.device.device_attrs.name", "device-1")

        assert device.get_pretty_name() == "device-1"
