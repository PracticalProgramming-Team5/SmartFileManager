class FileSystemManager:
    """
    실제 파일 시스템 작업을 실행하고 안전하게 수행되도록 보장합니다.
    """

    def __init__(self):
        """필요한 상태를 초기화합니다."""
        pass

    def move_file(self, source: str, destination: str) -> bool:
        """
        파일을 이동하고 성공 여부를 반환합니다.

        Args:
            source: 이동할 파일 경로
            destination: 대상 경로

        Returns:
            작업 성공 여부
        """
        pass

    def rename_item(self, path: str, new_name: str) -> bool:
        """
        파일 또는 디렉토리의 이름을 변경합니다.

        Args:
            path: 이름을 변경할 항목 경로
            new_name: 새 이름

        Returns:
            작업 성공 여부
        """
        pass

    def delete_item(self, path: str) -> bool:
        """
        파일 또는 디렉토리를 삭제합니다.

        Args:
            path: 삭제할 항목 경로

        Returns:
            작업 성공 여부
        """
        pass

    def create_directory(self, path: str) -> bool:
        """
        새 디렉토리를 생성합니다.

        Args:
            path: 생성할 디렉토리 경로

        Returns:
            작업 성공 여부
        """
        pass

    def get_item_metadata(self, path: str) -> dict:
        """
        메타데이터(크기, 유형, 날짜 등)를 가져옵니다.

        Args:
            path: 메타데이터를 가져올 항목 경로

        Returns:
            항목 메타데이터를 담은 사전
        """
        pass

    def list_directory_contents(self, path: str) -> list[str]:
        """
        파일 및 하위 디렉토리 목록을 가져옵니다.

        Args:
            path: 내용을 가져올 디렉토리 경로

        Returns:
            파일 및 하위 디렉토리 경로 목록
        """
        pass

    def path_exists(self, path: str) -> bool:
        """
        경로의 존재 여부를 확인합니다.

        Args:
            path: 확인할 경로

        Returns:
            경로 존재 여부
        """
        pass

    def execute_plan(self, actions: list[dict]) -> bool:
        """
        ResponseInterpreter가 제공한 작업 시퀀스를 실행합니다.

        Args:
            actions: 실행할 작업 시퀀스

        Returns:
            모든 작업의 성공 여부
        """
        pass

    def reverse_action(self, action_log: dict) -> bool:
        """
        기록된 특정 작업을 실행 취소하려고 시도합니다.

        Args:
            action_log: 실행 취소할 작업에 대한 세부 정보

        Returns:
            실행 취소 성공 여부
        """
        pass
