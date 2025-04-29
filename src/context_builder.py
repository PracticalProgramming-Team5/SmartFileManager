from pydantic import BaseModel, ValidationError, TypeAdapter
from typing import List, Dict, Tuple, Sequence, Optional
import json

# json 파싱 형식 정의
class ActionMove(BaseModel):
    source: str
    destination: Tuple[str, ...]
    explanation: Tuple[str, ...]
    def __repr__(self):
        return self.model_dump_json(indent=2)

class ActionCommand(BaseModel):
    action: str
    source: str
    destination: str
    def __repr__(self):
        return self.model_dump_json()

class ActionCommandList(BaseModel):
    plan: List[ActionCommand]
    explanation: str
    def __repr__(self):
        return self.model_dump_json(indent=2)


example_payload = ActionCommandList(
    plan=[
        ActionCommand(
            action="사용자 제공 API 1",
            source="some/source/path1",
            destination="some/dest/path1"
        ),
        ActionCommand(
            action="사용자 제공 API 2",
            source="some/source/path2",
            destination="some/dest/path2"
        )
    ],
    explanation="위 스크립트의 동작과정을 한 문장으로 설명"
)

example_payload_2 = ActionMove(
    source="some/source/path",
    destination=("dest/path1", "dest/path2", "dest/path3"),
    explanation=(
        "dest/path1을 추천하는 이유",
        "dest/path2을 추천하는 이유",
        "dest/path3을 추천하는 이유",
    )
)

class ContextBuilder:
    """
    LLM 프롬프트에 필요한 정보를 수집하고 형식화합니다.
    """
    system_prompt_script = "당신은 파일 시스템 자동화 스크립트 생성 전문가입니다.\n" \
        "사용자가 제공하는 API 사양에 따라 파일 이동·복사·삭제 등 파일 시스템 작업을 수행하는 Python 스크립트를 작성해 주세요.\n" \
        "생성된 스크립트가 어떤 역할을 어떻게 수행하는지 한 줄로 간략히 요약한 글을 작성해 주세요.\n" \
        "반드시 아래 json 스키마에 맞춰, JSON 이외의 텍스트를 전혀 포함하지 말고 출력해야 합니다:\n" \
        "```json\n" \
        f"{repr(example_payload)}\n" \
        "```"
    
    system_prompt_move = "당신은 파일 분류·정리 전문가입니다.\n" \
        "사용자의 전체 디렉토리 구조와 각 디렉토리에 속한 파일들의 태그(내용에서 추출된 키워드, 메타데이터 등)를 이해한 후,\n" \
        "새로 전달된 파일의 이름·태그·메타데이터를 바탕으로 적절한 저장 위치(디렉토리 경로) 3개를 추천해 주세요.\n" \
        "반드시 아래 json 스키마에 맞춰, JSON 이외의 텍스트를 전혀 포함하지 말고 출력해야 합니다:\n" \
        "```json\n" \
        f"{repr(example_payload_2)}\n" \
        "```"
    
    def __init__(self, filesystem_manager):
        """
        FileSystemManager에 대한 참조를 저장합니다.

        Args:
            filesystem_manager: FileSystemManager의 인스턴스
        """
        pass

    def _get_file_context(self, file_path: str, detail_level: str = "basic") -> dict:
        """
        관련 파일 정보(이름, 크기, 유형, 큰 파일의 경우 detail_level에 따라 부분 콘텐츠)를 추출합니다.

        Args:
            file_path: 파일 경로
            detail_level: 세부 정보 수준 (기본값은 'basic')

        Returns:
            파일 관련 컨텍스트 정보를 담은 사전
        """
        pass

    def _get_directory_structure(
        self, root_path: str, max_depth: int = 5, use_cache: bool = True
    ) -> str:
        """
        디렉토리 구조의 표현(예: 텍스트 트리, JSON)을 생성합니다.

        Args:
            root_path: 구조를 생성할 루트 디렉토리 경로
            max_depth: 탐색할 최대 디렉토리 깊이
            use_cache: 캐시된 결과 사용 여부

        Returns:
            디렉토리 구조 표현(문자열)
        """
        pass

    def format_move_prompt(self, file_context: dict, dir_structure: str) -> str:
        """
        파일의 목적지를 제안하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            file_context: 파일 관련 컨텍스트
            dir_structure: 디렉토리 구조 표현

        Returns:
            LLM에게 보낼 프롬프트
        """
        pass

    def format_command_prompt(self, user_command: str, dir_structure: str) -> str:
        """
        자연어 명령을 해석하거나 스크립트/계획을 생성하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            user_command: 사용자의 자연어 명령
            dir_structure: 디렉토리 구조 표현

        Returns:
            LLM에게 보낼 프롬프트
        """
        pass

# # 실행 예시
# if __name__ == "__main__":
#     print(ContextBuilder.system_prompt_script)
#     print(ContextBuilder.system_prompt_move)