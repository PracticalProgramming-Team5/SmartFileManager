import logging
from typing import Dict, List, Optional, Tuple
from settings_manager import SettingsManager
from enum import IntFlag, auto
from openai import OpenAI
from openai import error as OpenAIError
"""
JHS
api와의 stateless한 통신을 가정
"""
class LLMErrorCode(IntFlag):
    SUCCESS = 0
    UNKNOWN = auto()
    TIMEOUT = auto()
    CONN_ERR = auto()
    HTTP_ERR = auto()
    KEY_ERR = auto()

class LLMClient:
    """
    LLM API와의 통신을 처리하는 클래스

    Raise:
        ValueError: model_name or api_key == None
    """
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    filehandler = logging.FileHandler("llm_client.log")
    filehandler.setFormatter(formatter)
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(LLMClient.filehandler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.update_settings()

    @staticmethod
    def _make_message(system_msg: str, prompt: str) -> List[Dict[str, str]]:
        """
        message 생성
        """
        return [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ]

    def query(self, system_msg: str, prompt: str, temperature: float = 0.7, max_tokens: int = 1500) -> Tuple[Optional[str], LLMErrorCode]:
        """
        LLM API에 프롬프트를 보내고 응답을 반환합니다.

        Args:
            system_msg(str): LLM의 역할이 지정된 프롬프트
            prompt(str): LLM에게 질의할 프롬프트
            temperature(float, optional): 프롬프트 파라미터
            max_tokens(int, optional): 프롬프트 파라미터

        Returns:
            LLM의 응답 텍스트, 에러 코드(플래그)
        """
        ecode = LLMErrorCode.SUCCESS
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self._make_message(system_msg, prompt),
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30
            )
            self.logger.info("API request was successfully ended")
            return response.choices[0].message.content, ecode
        except OpenAIError.AuthenticationError as e:
            self.logger.error(f"Auth error: {e}")
            ecode |= LLMErrorCode.KEY_ERR
        except OpenAIError.Timeout as e:
            self.logger.error(f"Timeout error: {e}")
            ecode |= LLMErrorCode.TIMEOUT
        except OpenAIError.APIConnectionError as e:
            self.logger.error(f"Conn error: {e}")
            ecode |= LLMErrorCode.CONN_ERR
        except OpenAIError.APIError as e:
            self.logger.error(f"HTTP error: {e}")
            ecode |= LLMErrorCode.HTTP_ERR
        except Exception as e:
            self.logger.error(f"Unknown error: {e}")
            ecode |= LLMErrorCode.UNKNOWN
        self.logger.error(f"Error code: {ecode}")
        return None, ecode
    
    def update_settings(self, update_api_key : bool=True, update_model_name : bool=True) -> None:
        """
        LLM API key를 업데이트하는 함수입니다.

        Args:
            update_api_key(bool, optional): api_key 업데이트 여부
            update_model_name(bool, optional): model_name 업데이트 여부

        Raise:
            ValueError
        """
        if update_api_key:
            api_key = SettingsManager.get('api_key')
            if not api_key:
                self.logger.error("Failed to update API key")
                raise ValueError("no API key")
            self.client = OpenAI(api_key=api_key)
            self.logger.info("API key updated")
        if update_model_name:
            model_name = SettingsManager.get('model_name')
            if not model_name:
                self.logger.error("Failed to update model name")
                raise ValueError("no model name")
            self.model_name = model_name
            self.logger.info("model name updated")