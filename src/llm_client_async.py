import logging
from typing import Dict, List, Optional, Tuple
from settings_manager import SettingsManager
import openai
from llm_client import LLMClient, LLMErrorCode, CODE_MAP, _make_message
from openai import AsyncOpenAI
import asyncio

"""
JHS
api와의 stateless한 통신을 가정
"""

# logger 정의
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_logger = logging.getLogger("llm_client_async")
if not _logger.handlers:
    handler = logging.FileHandler("llm_client_async.log")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

class AsyncLLMClient(LLMClient):
    """
    LLM API와의 통신을 처리하는 클래스

    Raise:
        ValueError: model_name or api_key == None
    """
    def __init__(self):
        self.update_settings()
    
    async def aquery(self, system_msg: str, prompt: str, temperature: float = 0.7, max_tokens: int = 1500) -> Tuple[Optional[str], LLMErrorCode]:
        """
        LLM API에 프롬프트를 보내고 비동기적으로 응답을 반환합니다.

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
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=_make_message(system_msg, prompt),
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30
            )
            return response.choices[0].message.content, ecode
        except tuple(CODE_MAP.keys()) as e:
            _logger.error(f"{type(e).__name__}: {e}")
            ecode |= CODE_MAP[type(e)]
        except openai.APIError as e: # 기타 API 관련 에러들
            _logger.error(f"API error: {e}")
            ecode |= LLMErrorCode.API_ERR
        except Exception as e: # 이외 알 수 없는 오류
            _logger.error(f"Unknown error: {e}")
            ecode |= LLMErrorCode.UNKNOWN
        _logger.error(f"ecode: {ecode}")
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
                _logger.error("Failed to update API key")
                raise ValueError("no API key")
            self.client = AsyncOpenAI(api_key=api_key)
        if update_model_name:
            model_name = SettingsManager.get('model_name')
            if not model_name:
                _logger.error("Failed to update model name")
                raise ValueError("no model name")
            self.model_name = model_name

"""
# 예제 코드. 더 자유로운 구현을 위해선 threading을 통해 코드를 구현해야 할 듯
async def main():
    # 작업 설정
    client = AsyncLLMClient()
    task = asyncio.create_task(client.aquery("계산기", "2+2=?"))
    # 콜백 함수 설정
    def callback_func(task: asyncio.Task):
        res, _ = task.result()
        print(res)
    task.add_done_callback(callback_func)
    # 다음 명령어 실행하며 폴링
    for i in range(10):
        await asyncio.sleep(0.1)
        print(f"next line execute..{i}")
        if task.done():
            break
if __name__ == "__main__":
    asyncio.run(main())
"""