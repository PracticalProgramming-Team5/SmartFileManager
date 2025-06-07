class HistoryManager:
    _history = []
    __max_history = 20

    @classmethod
    def log(cls, action_details: dict) -> None:
        if len(cls._history) >= cls.__max_history:
            cls._history.pop(0)  # 가장 오래된 항목 제거
        cls._history.append(action_details)

    @classmethod
    def peek(cls) -> list | None:
        if cls._history:
            return cls._history[-1]
        return None

    @classmethod
    def delete(cls, index) -> None:
        if index >= 0 and cls._history and len(cls._history) > index:
            cls._history.pop(index)

    @classmethod
    def clear(cls) -> None:
        if cls._history:
            cls._history = []

    @classmethod
    def get(cls) -> list:
        return cls._history