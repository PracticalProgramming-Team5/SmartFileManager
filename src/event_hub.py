from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable
from dataclasses import dataclass

@dataclass
class AppEvent:
    name: str # 이벤트 유형
    data: object # 데이터


class EventHub(QObject):
    event = pyqtSignal(AppEvent)
    _initialized = False

    def __init__(self):
        if EventHub._initialized:
            raise RuntimeError("EventHub instance already initialized!")
        
        EventHub._initialized = True
        super().__init__()
    
    @classmethod
    def get_global_instance(cls):
        if not cls._initialized:
            cls._initialized = EventHub()
        return cls._initialized

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
