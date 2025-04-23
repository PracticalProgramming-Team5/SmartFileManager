import json
import re
from typing import List, Dict, Any


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
        suggestions = []

        # 1. [경로] - 이유 형식의 패턴 찾기
        pattern = r"\d+\.\s+\[([^\]]+)\]\s*-\s*(.+)"
        matches = re.findall(pattern, llm_response)

        if matches:
            for match in matches:
                path = match[0].strip()
                reason = match[1].strip() if len(match) > 1 else ""
                suggestions.append({"path": path, "reason": reason})

        # 패턴이 없을 경우 다른 형식 시도
        if not suggestions:
            # 번호. 경로 - 이유 형식 시도
            pattern2 = r"\d+\.\s*([^\n-]+)\s*-\s*(.+)"
            matches = re.findall(pattern2, llm_response)

            if matches:
                for match in matches:
                    path = match[0].strip()
                    reason = match[1].strip() if len(match) > 1 else ""
                    suggestions.append({"path": path, "reason": reason})

        # 여전히 결과가 없으면 일반 텍스트에서 경로 찾기
        if not suggestions:
            # 일반적인 파일 경로 패턴 시도
            path_pattern = r'(?:\/|\\|\w:)[^\s"\'*?<>|]+'
            paths = re.findall(path_pattern, llm_response)

            if paths:
                for path in paths:
                    suggestions.append({"path": path, "reason": "경로가 감지됨"})

        return suggestions

    def parse_action_plan(self, llm_response: str) -> list[dict]:
        """
        자연어 명령에 대한 LLM 응답을 해석하여 구조화된 작업 시퀀스를 생성합니다.

        Args:
            llm_response: LLM으로부터 받은 응답

        Returns:
            구조화된 작업 시퀀스 (예: [{'action': 'move', 'source': 'path/a', 'destination': 'path/b'}])
        """
        # JSON 형식 추출 시도
        try:
            # JSON 코드 블록 찾기
            json_pattern = r"```(?:json)?\s*({[\s\S]*?})```"
            matches = re.findall(json_pattern, llm_response)

            if matches:
                # 가장 긴 매치 사용 (여러 JSON 블록이 있을 경우)
                json_str = max(matches, key=len)
                parsed_data = json.loads(json_str)

                if "plan" in parsed_data and isinstance(parsed_data["plan"], list):
                    action_plan = parsed_data["plan"]
                    explanation = parsed_data.get("explanation", "")

                    # 계획에 설명 추가
                    for action in action_plan:
                        if "description" not in action and explanation:
                            action["description"] = explanation

                    return self._validate_action_plan(action_plan)

            # 중괄호로 직접 감싸진 JSON 찾기
            direct_json_pattern = r'{[\s\S]*?"plan"[\s\S]*?}'
            matches = re.findall(direct_json_pattern, llm_response)

            if matches:
                json_str = max(matches, key=len)
                parsed_data = json.loads(json_str)

                if "plan" in parsed_data and isinstance(parsed_data["plan"], list):
                    return self._validate_action_plan(parsed_data["plan"])

        except Exception as e:
            print(f"JSON 파싱 오류: {e}")

        # JSON 추출 실패 시 텍스트에서 작업 추출 시도
        plan = []

        # 이동 작업 (소스에서 대상으로)
        move_pattern = r'(?:이동|옮기|복사).*?[\'"`]([^\'"`]+)[\'"`].*?(?:에서|from).*?[\'"`]([^\'"`]+)[\'"`]|[\'"`]([^\'"`]+)[\'"`].*?(?:을|를).*?[\'"`]([^\'"`]+)[\'"`].*?(?:으?로|에)'
        for match in re.finditer(move_pattern, llm_response):
            groups = match.groups()
            if groups[0] and groups[1]:  # 첫 번째 패턴
                plan.append(
                    {
                        "action": "move",
                        "source": groups[0],
                        "destination": groups[1],
                        "description": "텍스트에서 파싱된 이동 작업",
                    }
                )
            elif groups[2] and groups[3]:  # 두 번째 패턴
                plan.append(
                    {
                        "action": "move",
                        "source": groups[2],
                        "destination": groups[3],
                        "description": "텍스트에서 파싱된 이동 작업",
                    }
                )

        # 이름 변경 작업
        rename_pattern = r'(?:이름 변경|rename).*?[\'"`]([^\'"`]+)[\'"`].*?[\'"`]([^\'"`]+)[\'"`]|[\'"`]([^\'"`]+)[\'"`].*?이름을.*?[\'"`]([^\'"`]+)[\'"`]'
        for match in re.finditer(rename_pattern, llm_response):
            groups = match.groups()
            if groups[0] and groups[1]:  # 첫 번째 패턴
                plan.append(
                    {
                        "action": "rename",
                        "path": groups[0],
                        "new_name": groups[1],
                        "description": "텍스트에서 파싱된 이름 변경 작업",
                    }
                )
            elif groups[2] and groups[3]:  # 두 번째 패턴
                plan.append(
                    {
                        "action": "rename",
                        "path": groups[2],
                        "new_name": groups[3],
                        "description": "텍스트에서 파싱된 이름 변경 작업",
                    }
                )

        # 여전히 결과가 없으면 빈 배열 반환
        return plan

    def _validate_action_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        작업 계획의 각 항목이 필수 필드를 갖고 있는지 확인합니다.

        Args:
            plan: 검증할 작업 계획

        Returns:
            검증된 작업 계획
        """
        valid_plan = []

        for action in plan:
            if "action" not in action:
                continue

            action_type = action["action"].lower()

            if action_type == "move":
                if "source" in action and "destination" in action:
                    valid_plan.append(action)
            elif action_type == "rename":
                if "path" in action and "new_name" in action:
                    valid_plan.append(action)
            elif action_type == "delete":
                if "path" in action:
                    valid_plan.append(action)
            elif action_type == "create_directory":
                if "path" in action:
                    valid_plan.append(action)
            # 그 외 알 수 없는 작업 유형은 무시

        return valid_plan
