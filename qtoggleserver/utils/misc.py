
import logging.handlers


class FifoMemoryHandler(logging.handlers.MemoryHandler):
    def __init__(self, capacity: int) -> None:
        super().__init__(capacity, flushLevel=logging.FATAL + 1)

    def flush(self) -> None:
        self.acquire()

        while len(self.buffer) > self.capacity:
            self.buffer.pop(0)

        self.release()
