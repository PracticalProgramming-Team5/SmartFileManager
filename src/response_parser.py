import re
from typing import List, Dict, Tuple, Sequence, Optional
from pydantic import BaseModel, ValidationError, TypeAdapter
import json
from settings_manager import SettingsManager
from context_type import ActionCommandList, ActionMove
from pathlib import Path

"""
JHS
"""

def _extract_json(text: str) -> str:
    """
    문자열로부터 json 구조 추출.
    """
    # ```json{ ... }``` 찾기
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
        return f"unavailable action: {action}"
    
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
        else: return f"cannot parse paths: {paths}"

        for p in paths:
            p=Path(p).resolve()
            if not any(p.is_relative_to(base) for base in base_paths):
                return f"unavailable path: {p}"
    return False

class ResponseParser:
    """
    LLM으로부터 받은 응답을 분석하고 구조화합니다.

    Note: 응답은 ```json{ ... } ``' 구조를 가져야 합니다.
    """
    actionlist_adapter = TypeAdapter(ActionCommandList)
    actionmove_adapter = TypeAdapter(ActionMove)

    @staticmethod
    def parse_action_move(llm_response: str) -> Optional[ActionMove]:
        """
        파일 이동에 대한 LLM 응답을 해석하여 명령어 구문을 반환합니다.

        Args:
            llm_response(str): LLM으로부터 받은 응답

        Returns:
            Tuple: return_value, is_err_msg
        """
        try:
            json_block = _extract_json(llm_response)
            val_data = ResponseParser.actionmove_adapter.validate_json(json_block)
            command = val_data.model_dump()
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            return f"cannot parse llm response: {e}", True
        
        if (result:= _check_command({'move'}, command)):
            return result, True
        return command, False

    @staticmethod
    def parse_action_command(llm_response: str) -> Optional[ActionCommandList]:
        """
        자연어 명령에 대한 LLM 응답을 해석하여 배치 명령어 구문을 반환합니다.

        Args:
            llm_response(str): LLM으로부터 받은 응답

        Returns:
            Tuple: return_value, is_err_msg
        """
        try:
            json_block = _extract_json(llm_response)
            val_data = ResponseParser.actionlist_adapter.validate_json(json_block)
            commands = val_data.model_dump()
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            return f"cannot parse llm response: {e}", True
        
        restrict = SettingsManager.get("available_apis")
        for command in commands['plan']:
            if (result:= _check_command(restrict, command)):
                return result, True
        return commands, False