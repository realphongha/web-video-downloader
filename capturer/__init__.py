from .playwright import PlaywrightCapturer
from .api import APICapturer

CAPTURERS = {
    "playwright": PlaywrightCapturer,
    "api": APICapturer
}
