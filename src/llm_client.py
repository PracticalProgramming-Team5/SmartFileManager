class LLMClient:
    """
    LLM API와의 통신을 처리합니다.
    """

    def __init__(self, api_key: str, model_name: str):
        """
        API 키와 모델 정보로 클라이언트를 설정합니다.

        Args:
            api_key: LLM API 인증 키
            model_name: 사용할 LLM 모델 이름
        """
        pass

    def query(self, prompt: str) -> str:
        """
        LLM API에 프롬프트를 보내고 원시 텍스트 응답을 반환합니다.

        Args:
            prompt: LLM에게 보낼 프롬프트

        Returns:
            LLM의 응답 텍스트
        """
        pass
