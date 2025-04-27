import re
from typing import List, Dict, Tuple
from pydantic import BaseModel, ValidationError, TypeAdapter
import json
import logging
"""
JHS
"""
# TODO: 나중에 context_builder.py로 이동
# json 파싱 형식 정의
class ActionCommand(BaseModel):
    action: str
    source: str
    destination: str
    def __repr__(self):
        pass # TODO: 프롬프트 입력에 사용될 repr

class ActionCommandList(BaseModel):
    plan: List[ActionCommand]
    explanation: str
    def __repr__(self):
        pass # TODO: 프롬프트 입력에 사용될 repr
# =====================================================
# logger 정의
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_logger = logging.getLogger("response_parser")
if not _logger.handlers:
    handler = logging.FileHandler("response_parser.log")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False

def _extract_json(text: str) -> str:
    """
    문자열로부터 json 구조 추출.
    """
    # ```json ... ``` 찾기
    match = re.search(r"```json\s*(\{.*?\}|\[.*?\])\s*```", text, re.S)
    if match: return match.group(1)
    # 만약 없다면 { ... } 찾기
    match = re.search(r"(\{[\s\S]*\})", text, re.S)
    if match: return match.group(1)
    raise ValueError("no json block in response str.")

def _check_commands(restrict : Tuple, *args):
    pass # TODO: restrict 안에 있는 action만 호출하는지 검사

class ResponseParser:
    """
    LLM으로부터 받은 응답을 분석하고 구조화합니다.

    Note: 응답은 \`\`\` json ... ``` 구조를 가져야 합니다.
    """
    actionlist_adapter = TypeAdapter(ActionCommandList)
    action_adapter = TypeAdapter(ActionCommand)

    @staticmethod
    def parse_action_move(llm_response: str) -> Dict[str,str] | None:
        """
        파일 이동에 대한 LLM 응답을 해석하여 명령어 구문을 반환합니다.

        Args:
            llm_response(str): LLM으로부터 받은 응답

        Returns:
            Dict[str,str]: 추출된 단일 명령어 구문 | None
        """
        try:
            json_block = _extract_json(llm_response)
            val_data = ResponseParser.action_adapter.validate_json(json_block)
            command = val_data.model_dump()
            print(command)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            _logger.error(f"{type(e).__name__}: {e}")
            return None
        # TODO: 실행 타당성 검사
        # if _check_commands({'move', 'rename', 'copy'}, command): ...

    @staticmethod
    def parse_action_command(llm_response: str) -> List[Dict[str,str]] | None:
        """
        자연어 명령에 대한 LLM 응답을 해석하여 배치 명령어 구문을 반환합니다.

        Args:
            llm_response(str): LLM으로부터 받은 응답

        Returns:
            List[Dict[str,str]]: 구조화된 명령어 구문 | None
        """
        try:
            json_block = _extract_json(llm_response)
            val_data = ResponseParser.actionlist_adapter.validate_json(json_block)
            commands = val_data.model_dump()
            print(commands)
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            _logger.error(f"{type(e).__name__}: {e}")
            return None
        # TODO: 실행 타당성 검사

# # 예제 코드
# action_str = """```json{
#   "plan": [
#     {
#       "action": "copy",
#       "source": "some/source/path",
#       "destination": "some/dest/path"
#     },
#     {
#       "action": "delete",
#       "source": "some/source/path",
#       "destination": ""
#     }
#   ],
#   "explanation": "some/source/path 파일을 some/dest/path로 이동합니다."
# }
# ```"""
# action_str2 = """ {
#   "plan": [
#     {
#       "action": "copy",
#       "source": "some/source/path",
#       "destination": "some/dest/path"
#     },
#     {
#       "action": "delete",
#       "source": "some/source/path",
#       "destination": ""
#     }
#   ],
#   "explanation": "some/source/path 파일을 some/dest/path로 이동합니다."
# }

# """
# move_str = """```json {
#     "action": "move",
#     "source": "소스 경로",
#     "destination": "대상 경로"
# }
# ```"""
# move_str2 = """{
#     "action": "move",
#     "source": "소스 경로",
#     "destination": "대상 경로"
# }"""
# if __name__ == "__main__":
    # ResponseParser.parse_action_command(action_str)
    # ResponseParser.parse_action_move(move_str)
    # print("다른 구조의 응답 파싱")
    # ResponseParser.parse_action_command(action_str2)
    # ResponseParser.parse_action_move(move_str2)