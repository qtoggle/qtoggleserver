class TestVirtualPortPersistence:
    async def test_to_persisted_includes_virtual_value(self):
        """to_persisted should include virtual_value."""
        from tests.unit.qtoggleserver.mock.ports import MockVirtualPort

        vport = MockVirtualPort("vport1")
        vport._virtual_value = 42

        result = await vport.to_persisted()

        assert result["virtual_value"] == 42

    async def test_to_persisted_none_virtual_value(self):
        """to_persisted should include virtual_value even if None."""
        from tests.unit.qtoggleserver.mock.ports import MockVirtualPort

        vport = MockVirtualPort("vport2")
        vport._virtual_value = None

        result = await vport.to_persisted()

        assert result["virtual_value"] is None

    async def test_from_persisted_restores_virtual_value(self):
        """from_persisted should restore virtual_value."""
        from tests.unit.qtoggleserver.mock.ports import MockVirtualPort

        vport = MockVirtualPort("vport3")
        data = {
            "virtual_value": 99,
            "last_read_value": 12,
            "last_read_timestamp": 1001,
        }

        await vport.from_persisted(data)

        assert vport._virtual_value == 99
        assert vport._last_read_value == (12, 1001)

    async def test_from_persisted_handles_missing_virtual_value(self):
        """from_persisted should handle missing virtual_value."""
        from tests.unit.qtoggleserver.mock.ports import MockVirtualPort

        vport = MockVirtualPort("vport4")
        data = {"last_read_value": 12, "last_read_timestamp": 1001}

        await vport.from_persisted(data)

        assert vport._virtual_value is None
        assert vport._last_read_value == (12, 1001)
