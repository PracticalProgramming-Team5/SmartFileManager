from typing import Dict, List, Optional, Tuple
from settings_manager import SettingsManager
from enum import IntFlag, auto
import openai
from openai import OpenAI

"""
JHS
api와의 stateless한 통신을 가정
"""
class LLMErrorCode(IntFlag):
    """
    에러 코드 목록
    https://platform.openai.com/docs/guides/error-codes
    """
    SUCCESS = 0
    UNKNOWN = auto()
    API_ERR = auto()
    RATE_LIM = auto()
    CONN_ERR = auto()
    KEY_ERR = auto()
    TIMEOUT = auto()

# 예외 처리를 위한 매핑
CODE_MAP = {
    openai.RateLimitError: LLMErrorCode.RATE_LIM,
    openai.APIConnectionError: LLMErrorCode.CONN_ERR,
    openai.AuthenticationError: LLMErrorCode.KEY_ERR,
    openai.APITimeoutError: LLMErrorCode.TIMEOUT
}

def _make_message(system_msg: str, prompt: str) -> List[Dict[str, str]]:
    """
    message 생성
    """
    return [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": prompt}
    ]

class LLMClient:
    """
    LLM API와의 통신을 처리하는 클래스

    Raise:
        ValueError: api 및 model 업데이트 실패 시

    """
    def __init__(self):
        self.update_settings()

    def query(self, system_msg: str, prompt: str, temperature: float = 0.0, max_tokens: int = 1500) -> Tuple[Optional[str], LLMErrorCode]:
        """
        LLM API에 프롬프트를 보내고 응답을 반환합니다.

        Args:
            system_msg(str): LLM의 역할이 지정된 프롬프트
            prompt(str): LLM에게 질의할 프롬프트
            temperature(float, optional): 프롬프트 파라미터
            max_tokens(int, optional): 프롬프트 파라미터

        Returns:
            Tuple(str, LLMErrorCode): LLM의 응답 텍스트, 에러 코드(플래그)
        """
        ecode = LLMErrorCode.SUCCESS
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=_make_message(system_msg, prompt),
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30
            )
            return response.choices[0].message.content, ecode
        except tuple(CODE_MAP.keys()) as e: # 특정한 에러 코드들
            ecode |= CODE_MAP[type(e)]
        except openai.APIError as e: # 기타 API 관련 에러들
            ecode |= LLMErrorCode.API_ERR
        except Exception as e: # 이외 알 수 없는 오류
            ecode |= LLMErrorCode.UNKNOWN
        return None, ecode
    
    def update_settings(self, update_api_key : bool=True, update_model_name : bool=True) -> None:
        """
        LLM API key를 업데이트하는 함수입니다.

        Args:
            update_api_key(bool, optional): api_key 업데이트 여부
            update_model_name(bool, optional): model_name 업데이트 여부

        Raises:
            ValueError: model_name or api_key == None
        """
        if update_api_key:
            api_key = SettingsManager.get('api_key')
            if not api_key:
                raise ValueError("no API key")
            self.client = OpenAI(api_key=api_key)
        if update_model_name:
            model_name = SettingsManager.get('model_name')
            if not model_name:
                raise ValueError("no model name")
            self.model_name = model_name