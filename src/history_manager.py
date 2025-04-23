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
        pass

    def log_action(self, action_details: dict):
        """
        완료된 작업의 세부 정보(작업을 되돌리는 데 필요한 정보 포함)를 기록 스택에 추가합니다.

        Args:
            action_details: 작업에 대한 세부 정보를 담은 사전
        """
        pass

    def get_last_action(self) -> dict | None:
        """
        가장 최근 작업의 세부 정보를 제거하지 않고 반환합니다.

        Returns:
            가장 최근 작업 세부 정보 또는 기록이 없는 경우 None
        """
        pass

    def pop_last_action(self) -> dict | None:
        """
        가장 최근 작업의 세부 정보를 반환하고 제거합니다 (성공적인 실행 취소 후 사용됨).

        Returns:
            가장 최근 작업 세부 정보 또는 기록이 없는 경우 None
        """
        pass
