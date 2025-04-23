class ContextBuilder:
    """
    LLM 프롬프트에 필요한 정보를 수집하고 형식화합니다.
    """

    def __init__(self, filesystem_manager):
        """
        FileSystemManager에 대한 참조를 저장합니다.

        Args:
            filesystem_manager: FileSystemManager의 인스턴스
        """
        pass

    def get_file_context(self, file_path: str, detail_level: str = "basic") -> dict:
        """
        관련 파일 정보(이름, 크기, 유형, 큰 파일의 경우 detail_level에 따라 부분 콘텐츠)를 추출합니다.

        Args:
            file_path: 파일 경로
            detail_level: 세부 정보 수준 (기본값은 'basic')

        Returns:
            파일 관련 컨텍스트 정보를 담은 사전
        """
        pass

    def get_directory_structure(
        self, root_path: str, max_depth: int = 5, use_cache: bool = True
    ) -> str:
        """
        디렉토리 구조의 표현(예: 텍스트 트리, JSON)을 생성합니다.

        Args:
            root_path: 구조를 생성할 루트 디렉토리 경로
            max_depth: 탐색할 최대 디렉토리 깊이
            use_cache: 캐시된 결과 사용 여부

        Returns:
            디렉토리 구조 표현(문자열)
        """
        pass

    def format_move_prompt(self, file_context: dict, dir_structure: str) -> str:
        """
        파일의 목적지를 제안하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            file_context: 파일 관련 컨텍스트
            dir_structure: 디렉토리 구조 표현

        Returns:
            LLM에게 보낼 프롬프트
        """
        pass

    def format_command_prompt(self, user_command: str, dir_structure: str) -> str:
        """
        자연어 명령을 해석하거나 스크립트/계획을 생성하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            user_command: 사용자의 자연어 명령
            dir_structure: 디렉토리 구조 표현

        Returns:
            LLM에게 보낼 프롬프트
        """
        pass
