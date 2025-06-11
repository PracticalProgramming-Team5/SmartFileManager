from pynput import keyboard
from PyQt5.QtCore import pyqtSignal, QThread
from event_hub import EventHub, AppEvent

"""
    이벤트명: key (1:1 매칭이여야함)
"""
class HotKeyManager(QThread):
    def __init__(self):
        super().__init__()
        self.current_keys = set()
        self.hotkeys = {}
        self.event_hub = EventHub.get_global_instance()

    def run(self):
        with keyboard.Listener(on_press=self.__on_press, on_release=self.__on_release) as listener:
            listener.join()

    def __send_event_if_hot_key(self):
        for hotkey in self.hotkeys.keys():
            if all(k in self.current_keys for k in self.hotkeys[hotkey]):
                self.event_hub.event.emit(AppEvent(hotkey, None))

    def __on_press(self, key):
        self.current_keys.add(key)
        self.__send_event_if_hot_key()
    
    def __on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)
    
    def add(self, event_name, hotkey):
        self.hotkeys[event_name] = hotkey