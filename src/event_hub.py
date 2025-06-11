from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QRunnable
from dataclasses import dataclass
from llm_client import LLMErrorCode

@dataclass
class AppEvent:
    name: str # 이벤트 유형
    data: object # 데이터


class EventHub(QObject):
    event = pyqtSignal(AppEvent)
    # UI <-> Core Communication Event
    started_from_ui = pyqtSignal()
    stopped_from_ui = pyqtSignal()
    state_responded_from_core = pyqtSignal(bool)

    command_requested_from_ui = pyqtSignal(str) # message
    command_responded_from_core = pyqtSignal(bool, list, str) # is_err, Actions, Explanation

    operation_requested_from_ui = pyqtSignal(list, str) # Actions, Explanation
    operation_responded_from_core = pyqtSignal(bool, str) # is_err, Message

    suggestion_responded_from_core = pyqtSignal(bool, str, list, list) # is_err, Src path, Recommended paths, Reasons
    suggestion_accepted_from_ui = pyqtSignal(list, str) # Src paths, Dest path
    suggestion_opperated_from_core = pyqtSignal(bool, str) # is_err, Message

    history_requested_from_ui = pyqtSignal()
    history_responded_from_core = pyqtSignal()


    # Core Side Communication Event
    command_responded_from_llm = pyqtSignal(LLMErrorCode, str) # is_err, Response Message
    suggestion_responded_from_llm = pyqtSignal(LLMErrorCode, str) # Src path, Recommended paths, Reasons 
    tag_responded_from_llm = pyqtSignal()

    operation_responded_from_script = pyqtSignal(bool, str) # is_err, Message
    move_responded_from_script = pyqtSignal(bool, str) # is_err, Message

    add_monitored = pyqtSignal(str) # Path
    move_monitored = pyqtSignal(str, str) # Src path, Dest path
    del_monitored = pyqtSignal(str) # Path

    
    # UI Side Communication Event
    window_opened = pyqtSignal()
    input_opened = pyqtSignal()
    recommend_opended = pyqtSignal()


    # Singleton state
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
    def __init__(self, callback=None):
        super().__init__()
        self.callback = callback

    # @pyqtSlot()
    def run(self):
        try:
            if not self.callback:
                return
            
            self.callback()

        except Exception as e:
            print("error:", e)
