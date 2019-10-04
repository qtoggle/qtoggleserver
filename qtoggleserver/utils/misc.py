
import logging.handlers


class FifoMemoryHandler(logging.handlers.MemoryHandler):
    def __init__(self, capacity):
        logging.handlers.MemoryHandler.__init__(self, capacity, flushLevel=logging.FATAL + 1)

    def flush(self):
        self.acquire()

        while len(self.buffer) > self.capacity:
            self.buffer.pop(0)

        self.release()
