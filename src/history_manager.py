class HistoryManager:
    def __init__(self, max_history: int = 20):
        self.history = []
        self.max_history = max_history

    def log_action(self, action_details: dict):
        if len(self.history) >= self.max_history:
            self.history.pop(0)  # 가장 오래된 항목 제거
        self.history.append(action_details)

    def get_last_action(self) -> dict | None:
        if self.history:
            return self.history[-1]
        return None

    def pop_last_action(self) -> dict | None:
        if self.history:
            return self.history.pop()
        return None