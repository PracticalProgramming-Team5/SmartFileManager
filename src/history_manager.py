class HistoryManager:
    def __init__(self, max_history: int = 20):
        self._history = []
        self.__max_history = max_history

    def log(self, action_details: dict) -> None:
        if len(self._history) >= self.__max_history:
            self._history.pop(0)  # 가장 오래된 항목 제거
        self._history.append(action_details)

    def peek(self) -> list | None:
        if self._history:
            return self._history[-1]
        return None

    def delete(self, index) -> None:
        if index >= 0 and self._history and len(self._history) > index:
            del self._history[index]

    def get(self) -> list:
        return self._history