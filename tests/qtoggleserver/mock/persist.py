from qtoggleserver.drivers.persist.json import JSONDriver, UnindexedData


class MockPersistDriver(JSONDriver):
    def __init__(self) -> None:
        super().__init__(file_path=None)

        self._history_supported: bool = False

    def _load(self) -> UnindexedData:
        return {}

    def _save(self, data: UnindexedData) -> None:
        pass

    def enable_history_support(self) -> None:
        self._history_supported = True

    def is_history_supported(self) -> bool:
        return self._history_supported
