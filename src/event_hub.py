from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable
from dataclasses import dataclass

@dataclass
class AppEvent:
    name: str # 이벤트 유형
    data: object # 데이터


class EventHub(QObject):
    event = pyqtSignal(AppEvent)
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EventHub, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            super().__init__()
            self._initialized = True

class Worker(QRunnable):
    def __init__(self, callback=None, event_hub=None, name=None):
        super().__init__()
        self.callback = callback
        self.event_hub = event_hub
        self.name = name

    @pyqtSlot()
    def run(self):
        try:
            result = None
            if not self.callback:
                return
            
            result = self.callback()

            self.event_hub.event.emit(AppEvent(self.name, result))
        except Exception as e:
            print("error:", e)
