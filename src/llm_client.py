import json
import requests
from typing import Dict, List
from settings_manager import SettingsManager
"""
JHS
api와의 stateless한 통신을 가정함
"""

class LLMClient:
    """
    LLM API와의 통신을 처리하는 클래스
    """

    def __init__(self):
        self.api_endpoint = "https://api.openai.com/v1/chat/completions" # TODO

    def _make_header(self) -> Dict[str,str]:
        """
        기본 헤더 생성
        """
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SettingsManager.get("api_key")}",
        }

    def _make_message(self, system_msg: str, prompt: str) -> List[Dict[str, str]]:
        """
        message 생성
        """
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]

    def query(self, system_msg: str, prompt: str, temperature: float = 0.7, max_tokens: int = 1500) -> str:
        """
        LLM API에 프롬프트를 보내고 응답을 반환합니다.

        Args:
            system_msg(str): LLM의 역할이 지정된 프롬프트
            prompt(str): LLM에게 질의할 프롬프트
            temperature(float, optional): 프롬프트 파라미터
            max_tokens(int, optional): 프롬프트 파라미터

        Returns:
            LLM의 응답 텍스트
        """
        payload = {
            "model": SettingsManager.get("model_name"),
            "messages": self._make_message(system_msg, prompt),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            response = requests.post(
                self.api_endpoint,
                headers=self._make_header(),
                data=json.dumps(payload),
                timeout=30,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return "API 요청 시간이 초과되었습니다."
        except requests.exceptions.ConnectionError:
            return "API 연결 오류가 발생했습니다."
        except requests.exceptions.HTTPError as e:
            return f"HTTP 오류 발생: {str(e)}"
        except Exception as e:
            error_msg = f"예상치 못한 오류 발생: {str(e)}"
            print(error_msg)
            return f"오류 발생: {str(e)}"
        # TODO: api_key 없음 오류에 대한 예외 처리 필요
        # if response.status_code == 200:
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"]