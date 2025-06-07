from PyQt5.QtCore import QObject, pyqtSignal
from dataclasses import dataclass

@dataclass
class AppEvent:
    target: str # 대상
    type: str # 이벤트 유형
    data: object # 데이터


class EventHub(QObject):
    event = pyqtSignal(AppEvent)