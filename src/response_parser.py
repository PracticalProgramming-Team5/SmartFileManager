import re
from typing import List, Dict, Tuple, Sequence
from pydantic import BaseModel, ValidationError, TypeAdapter
import json
import logging
from settings_manager import SettingsManager
from pathlib import Path

"""
JHS
"""

# TODO: 나중에 context_builder.py로 이동
# json 파싱 형식 정의
class ActionMove(BaseModel):
    source: str
    destination: Tuple[str]
    explanation: Tuple[str]
    def __repr__(self):
        pass # TODO: 프롬프트 입력에 사용될 repr

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

def _check_command(restrict : Tuple, cmd : Dict) -> bool:
    """
    해석된 명령이 타당한지 검사
    1. action이 허용된 api로만 구성되는가?
    2. source / destination이 감시 중인 디렉토리의 하위 폴더인가?
    """
    action = cmd.get("action")
    if action and action not in restrict:
        _logger.error(f"wrong action called: {action}")
        return False
    
    observing_dirs = SettingsManager.get("available_dirs")
    base_paths = [Path(d).resolve() for d in observing_dirs]

    for key in ("source", "destination"):
        k = cmd.get(key)
        if not k: continue

        paths = None
        if isinstance(k, str):
            paths = [k]
        elif isinstance(k, Sequence):
            paths = k
        else: return False

        for p in paths:
            p=Path(p).resolve()
            if not any(p.is_relative_to(base) for base in base_paths):
                return False
    return True

class ResponseParser:
    """
    LLM으로부터 받은 응답을 분석하고 구조화합니다.

    Note: 응답은 \`\`\` json ... ``` 구조를 가져야 합니다.
    """
    actionlist_adapter = TypeAdapter(ActionCommandList)
    actionmove_adapter = TypeAdapter(ActionMove)

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
            val_data = ResponseParser.actionmove_adapter.validate_json(json_block)
            command = val_data.model_dump()
            # print(command)
            # print(type(command))
            if _check_command({'move', 'rename', 'copy'}, command): 
                return command
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            _logger.error(f"{type(e).__name__}: {e}")
        return None

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
            # print(commands)
            # print(type(commands))
            restrict = SettingsManager.get("available_apis")
            if all(_check_command(restrict, command) for command in commands):
                return commands
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            _logger.error(f"{type(e).__name__}: {e}")
        return None

# # 예제 코드. SettingsManager 미구현 시 실행 과정에서 오류가 발생함.
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
#     ResponseParser.parse_action_command(action_str)
#     ResponseParser.parse_action_move(move_str)
#     print("다른 구조의 응답 파싱")
#     ResponseParser.parse_action_command(action_str2)
#     ResponseParser.parse_action_move(move_str2)