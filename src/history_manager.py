from collections import deque
from typing import Dict, Optional, List, Any


class HistoryManager:
    """
    실행 취소(undo) 기능을 위해 실행된 파일 작업을 기록합니다.
    """

    def __init__(self, max_history: int = 20):
        """
        최대 실행 취소 단계 수를 설정합니다.

        Args:
            max_history: 저장할 최대 작업 기록 수
        """
        self.max_history = max_history
        self.history = deque(maxlen=max_history)

    def log_action(self, action_details: dict):
        """
        완료된 작업의 세부 정보(작업을 되돌리는 데 필요한 정보 포함)를 기록 스택에 추가합니다.

        Args:
            action_details: 작업에 대한 세부 정보를 담은 사전
        """
        # 타임스탬프 추가 (이미 있으면 업데이트하지 않음)
        if "timestamp" not in action_details:
            import datetime

            action_details["timestamp"] = datetime.datetime.now().isoformat()

        # 기록에 추가
        self.history.append(action_details)

    def get_last_action(self) -> dict | None:
        """
        가장 최근 작업의 세부 정보를 제거하지 않고 반환합니다.

        Returns:
            가장 최근 작업 세부 정보 또는 기록이 없는 경우 None
        """
        if not self.history:
            return None
        return self.history[-1]

    def pop_last_action(self) -> dict | None:
        """
        가장 최근 작업의 세부 정보를 반환하고 제거합니다 (성공적인 실행 취소 후 사용됨).

        Returns:
            가장 최근 작업 세부 정보 또는 기록이 없는 경우 None
        """
        if not self.history:
            return None
        return self.history.pop()

    def get_history(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        작업 기록의 전체 또는 일부를 반환합니다.

        Args:
            limit: 반환할 최근 기록의 개수 (None이면 전체 기록)

        Returns:
            작업 기록 목록 (최신 항목이 마지막에 위치)
        """
        if limit is None or limit >= len(self.history):
            return list(self.history)
        else:
            return list(self.history)[-limit:]

    def clear_history(self):
        """
        전체 작업 기록을 삭제합니다.
        """
        self.history.clear()

    def get_history_count(self) -> int:
        """
        현재 기록된 작업 수를 반환합니다.

        Returns:
            기록된 작업 수
        """
        return len(self.history)
