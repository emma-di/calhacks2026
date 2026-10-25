"""Read session-only test controls from the receiver; failures restore normal suppression."""
import json
import time
from urllib.request import urlopen


class RecognitionControls:
    def __init__(self, endpoint=None):
        self.url = endpoint.rsplit('/events', 1)[0] + '/health' if endpoint and endpoint.endswith('/events') else None
        self.checked = -float('inf')
        self.repeat_suppression = True
        self.snap_to_dismiss = False
        self.active_event_id = None

    def refresh(self):
        now = time.monotonic()
        if self.url and now - self.checked >= 1:
            self.checked = now
            try:
                with urlopen(self.url, timeout=0.2) as response:
                    health = json.load(response)
                value = health.get('repeat_suppression', True)
                self.repeat_suppression = value if isinstance(value, bool) else True
                self.snap_to_dismiss = health.get('snap_to_dismiss') is True
                active = health.get('active_event_id')
                self.active_event_id = active if isinstance(active, str) else None
            except (OSError, ValueError, AttributeError):
                self.repeat_suppression = True
                self.snap_to_dismiss = False
                self.active_event_id = None
        return self.repeat_suppression
