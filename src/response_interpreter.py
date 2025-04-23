class ResponseInterpreter:
    """
    LLM으로부터 받은 응답을 분석하고 구조화합니다.
    """

    def parse_move_suggestions(self, llm_response: str) -> list[str]:
        """
        파일 이동에 대한 LLM 응답에서 가능한 대상 경로들을 추출합니다.

        Args:
            llm_response: LLM으로부터 받은 응답

        Returns:
            추출된 대상 경로 목록
        """
        pass

    def parse_action_plan(self, llm_response: str) -> list[dict]:
        """
        자연어 명령에 대한 LLM 응답을 해석하여 구조화된 작업 시퀀스를 생성합니다.

        Args:
            llm_response: LLM으로부터 받은 응답

        Returns:
            구조화된 작업 시퀀스 (예: [{'action': 'move', 'source': 'path/a', 'destination': 'path/b'}])
        """
        pass
