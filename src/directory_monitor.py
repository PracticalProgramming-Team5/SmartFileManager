class DirectoryMonitor:
    """
    지정된 디렉토리에서 새 파일 생성이나 관련 변경 사항을 감시합니다.
    """

    def __init__(self, core_controller):
        """
        FileManagerCore에 대한 참조를 저장합니다.

        Args:
            core_controller: FileManagerCore의 인스턴스
        """
        pass

    def add_directory(self, path: str):
        """
        감시 목록에 디렉토리를 추가합니다.

        Args:
            path: 감시할 디렉토리 경로
        """
        pass

    def remove_directory(self, path: str):
        """
        감시 목록에서 디렉토리를 제거합니다.

        Args:
            path: 감시 목록에서 제거할 디렉토리 경로
        """
        pass

    def start(self):
        """감시 루프를 시작합니다 (별도의 스레드/프로세스에서 실행될 수 있음)."""
        pass

    def stop(self):
        """감시 루프를 중지합니다."""
        pass

    def _on_file_created(self, file_path: str):
        """
        새 파일이 감지되었을 때 호출되는 내부 함수;
        FileManagerCore의 handle_new_file을 호출합니다.

        Args:
            file_path: 새로 생성된 파일 경로
        """
        pass
