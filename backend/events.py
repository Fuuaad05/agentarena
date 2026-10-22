from datetime import datetime, timezone
from typing import Callable, Optional


EventCallback = Callable[[dict], None]


class EventEmitter:
    def __init__(self, callback: Optional[EventCallback] = None):
        self.callback = callback

    def emit(self, stage: str, status: str, message: str):
        event = {
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        if self.callback:
            self.callback(event)

        return event