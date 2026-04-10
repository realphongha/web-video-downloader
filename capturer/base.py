from abc import ABC, abstractmethod

class CaptureResult:
    def __init__(self, url, stream_type, headers=None):
        self.url = url
        self.stream_type = stream_type
        self.headers = headers or {}


class BaseCapturer(ABC):
    @abstractmethod
    def capture(self) -> CaptureResult:
        pass
