import json
import requests
from typing import Dict, Any, Optional, Union, cast


class LLMClient:
    """
    LLM API와의 통신을 처리합니다.
    """

    def __init__(self, api_key: str, model_name: str) -> None:
        """
        API 키와 모델 정보로 클라이언트를 설정합니다.

        Args:
            api_key: LLM API 인증 키
            model_name: 사용할 LLM 모델 이름
        """
        self.api_key: str = api_key
        self.model_name: str = model_name
        self.api_endpoint: str = "https://api.openai.com/v1/chat/completions"
        self.headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def query(self, prompt: str) -> str:
        """
        LLM API에 프롬프트를 보내고 원시 텍스트 응답을 반환합니다.

        Args:
            prompt: LLM에게 보낼 프롬프트

        Returns:
            LLM의 응답 텍스트
        """
        if not self.api_key:
            return "API 키가 설정되지 않았습니다. 설정에서 API 키를 추가해주세요."

        try:
            payload: Dict[str, Any] = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1500,
            }

            response = requests.post(
                self.api_endpoint,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=30,
            )

            if response.status_code == 200:
                response_json: Dict[str, Any] = response.json()
                return cast(str, response_json["choices"][0]["message"]["content"])
            else:
                error_msg: str = f"API 오류: {response.status_code} - {response.text}"
                print(error_msg)
                return f"API 요청 중 오류가 발생했습니다: {response.status_code}"

        except requests.exceptions.Timeout:
            return "API 요청 시간이 초과되었습니다."
        except requests.exceptions.ConnectionError:
            return "API 연결 오류가 발생했습니다."
        except Exception as e:
            error_msg: str = f"예상치 못한 오류 발생: {str(e)}"
            print(error_msg)
            return f"오류 발생: {str(e)}"

    def update_settings(
        self, api_key: Optional[str] = None, model_name: Optional[str] = None
    ) -> None:
        """
        LLM 클라이언트 설정을 업데이트합니다.

        Args:
            api_key: 새 API 키 (None이면 변경 안 함)
            model_name: 새 모델 이름 (None이면 변경 안 함)
        """
        if api_key:
            self.api_key = api_key
            self.headers["Authorization"] = f"Bearer {api_key}"

        if model_name:
            self.model_name = model_name
