import os
import mimetypes
import json
from typing import Dict, Any, List
import time


class ContextBuilder:
    """
    LLM 프롬프트에 필요한 정보를 수집하고 형식화합니다.
    """

    def __init__(self, filesystem_manager):
        """
        FileSystemManager에 대한 참조를 저장합니다.

        Args:
            filesystem_manager: FileSystemManager의 인스턴스
        """
        self.filesystem_manager = filesystem_manager
        self.dir_structure_cache = {}  # 키: 경로, 값: (구조, 타임스탬프)
        self.cache_ttl = 300  # 5분 캐시 유효 시간

    def get_file_context(self, file_path: str, detail_level: str = "basic") -> dict:
        """
        관련 파일 정보(이름, 크기, 유형, 큰 파일의 경우 detail_level에 따라 부분 콘텐츠)를 추출합니다.

        Args:
            file_path: 파일 경로
            detail_level: 세부 정보 수준 (기본값은 'basic')

        Returns:
            파일 관련 컨텍스트 정보를 담은 사전
        """
        # 파일 메타데이터 가져오기
        metadata = self.filesystem_manager.get_item_metadata(file_path)

        if not metadata.get("exists", False):
            return {"error": "파일이 존재하지 않습니다"}

        file_context = {
            "name": metadata.get("name", ""),
            "path": metadata.get("path", ""),
            "size": metadata.get("size", 0),
            "created": metadata.get("created", ""),
            "modified": metadata.get("modified", ""),
            "extension": metadata.get("extension", ""),
            "mime_type": self._get_mime_type(file_path),
            "is_binary": self._is_binary_file(file_path),
        }

        # 파일 내용이 필요한 경우 (텍스트 파일이고 일정 크기 이하인 경우)
        if (
            not file_context["is_binary"] and file_context["size"] < 1024 * 1024
        ):  # 1MB 미만
            try:
                if detail_level == "full":
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        file_context["content"] = f.read()
                elif detail_level == "partial":
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        # 처음 50줄과 마지막 20줄만 포함
                        lines = f.readlines()
                        if len(lines) <= 70:
                            file_context["content"] = "".join(lines)
                        else:
                            file_context["content"] = (
                                "".join(lines[:50])
                                + "\n...(중략)...\n"
                                + "".join(lines[-20:])
                            )
            except Exception as e:
                file_context["error"] = f"파일 내용 읽기 실패: {str(e)}"

        return file_context

    def get_directory_structure(
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
        # 캐시 확인
        if use_cache and root_path in self.dir_structure_cache:
            cached_structure, timestamp = self.dir_structure_cache[root_path]
            if time.time() - timestamp < self.cache_ttl:
                return cached_structure

        try:
            # 디렉토리 구조를 트리 형태의 텍스트로 생성
            structure = self._build_tree_structure(root_path, max_depth)

            # 캐시 업데이트
            self.dir_structure_cache[root_path] = (structure, time.time())

            return structure

        except Exception as e:
            return f"디렉토리 구조 생성 중 오류 발생: {str(e)}"

    def format_move_prompt(self, file_context: dict, dir_structure: str) -> str:
        """
        파일의 목적지를 제안하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            file_context: 파일 관련 컨텍스트
            dir_structure: 디렉토리 구조 표현

        Returns:
            LLM에게 보낼 프롬프트
        """
        prompt = f"""
당신은 파일 시스템 관리를 도와주는 AI 비서입니다. 사용자의 디렉토리 구조를 분석하고, 새 파일을 저장하기에 가장 적합한 위치를 추천해주세요.

### 현재 디렉토리 구조:
{dir_structure}

### 파일 정보:
- 이름: {file_context.get('name', '알 수 없음')}
- 확장자: {file_context.get('extension', '없음')}
- 생성일: {file_context.get('created', '알 수 없음')}
- 수정일: {file_context.get('modified', '알 수 없음')}
- 파일 유형: {file_context.get('mime_type', '알 수 없음')}
"""

        # 텍스트 파일이고 내용이 있는 경우 내용 일부 추가
        if not file_context.get("is_binary", True) and "content" in file_context:
            content = file_context["content"]
            if len(content) > 500:  # 내용이 너무 길면 앞부분만 사용
                content = content[:500] + "...(생략)"
            prompt += f"\n### 파일 내용 일부:\n{content}\n"

        prompt += """
### 요청:
이 파일을 적절한 폴더에 분류하려고 합니다. 디렉토리 구조를 분석하여 이 파일을 저장하기에 가장 적합한 위치를 3가지 추천해 주세요.
반드시 기존 디렉토리 구조에 있는 경로만 추천하세요. 없는 경로는 추천하지 마세요.

각 추천에 대해 다음 형식으로 답변해주세요:
1. [대상 경로] - [추천 이유]
2. [대상 경로] - [추천 이유]
3. [대상 경로] - [추천 이유]

현재 경로를 그대로 두는 것이 좋다면, 그 이유와 함께 설명해주세요.
"""
        return prompt

    def format_command_prompt(self, user_command: str, dir_structure: str) -> str:
        """
        자연어 명령을 해석하거나 스크립트/계획을 생성하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            user_command: 사용자의 자연어 명령
            dir_structure: 디렉토리 구조 표현

        Returns:
            LLM에게 보낼 프롬프트
        """
        return f"""
당신은 파일 시스템 관리를 위한 AI 비서입니다. 사용자가 자연어로 요청한 작업을 정확하게 이해하고, 실행 가능한 작업 계획으로 변환해주세요.

### 현재 디렉토리 구조:
{dir_structure}

### 사용자 요청:
{user_command}

### 수행할 작업 계획을 다음 JSON 형식으로 제공해주세요:
```json
{{
  "plan": [
    {{
      "action": "move",
      "source": "소스 경로",
      "destination": "대상 경로",
      "description": "이 작업을 수행하는 이유"
    }},
    {{
      "action": "rename",
      "path": "대상 파일/폴더 경로",
      "new_name": "새 이름",
      "description": "이 작업을 수행하는 이유"
    }},
    ...
  ],
  "explanation": "전체 작업 계획에 대한 간략한 설명"
}}
```

지원하는 작업 유형:
- move: 파일 또는 디렉토리 이동
- rename: 파일 또는 디렉토리 이름 변경
- delete: 파일 또는 디렉토리 삭제
- create_directory: 새 디렉토리 생성

주의사항:
1. 현재 디렉토리 구조에 존재하는 경로만 사용하세요.
2. 각 작업에 대한 설명을 포함해주세요.
3. 사용자의 요청을 충실히 이행하는 계획을 작성하세요.
4. 특별한 요청이 없다면 파일을 삭제하는 작업은 권장하지 마세요.
"""

    def _get_mime_type(self, file_path: str) -> str:
        """
        파일의 MIME 유형을 반환합니다.

        Args:
            file_path: 파일 경로

        Returns:
            MIME 유형
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def _is_binary_file(self, file_path: str) -> bool:
        """
        파일이 바이너리 파일인지 확인합니다.

        Args:
            file_path: 파일 경로

        Returns:
            바이너리 파일 여부
        """
        mime = self._get_mime_type(file_path)

        # 텍스트 기반 MIME 유형 목록
        text_mimes = [
            "text/",
            "application/json",
            "application/xml",
            "application/javascript",
        ]

        for text_mime in text_mimes:
            if mime and mime.startswith(text_mime):
                return False

        # MIME 유형으로 판단할 수 없는 경우 파일 내용으로 확인
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)  # 파일의 첫 1KB만 읽음

            # NULL 바이트가 포함되어 있으면 바이너리로 판단
            return b"\x00" in chunk

        except Exception:
            return True  # 오류 발생 시 안전하게 바이너리로 간주

    def _build_tree_structure(
        self, root_path: str, max_depth: int, current_depth: int = 0, prefix: str = ""
    ) -> str:
        """
        디렉토리 구조를 트리 형태로 재귀적으로 구성합니다.

        Args:
            root_path: 현재 디렉토리 경로
            max_depth: 최대 탐색 깊이
            current_depth: 현재 탐색 깊이
            prefix: 현재 줄의 접두사

        Returns:
            트리 형태의 디렉토리 구조
        """
        if current_depth > max_depth:
            return prefix + "...(최대 깊이 도달)\n"

        if not os.path.exists(root_path) or not os.path.isdir(root_path):
            return ""

        result = prefix + os.path.basename(root_path) + "/\n"

        try:
            entries = sorted(os.listdir(root_path))

            # 디렉토리와 파일 분리
            dirs = [
                entry
                for entry in entries
                if os.path.isdir(os.path.join(root_path, entry))
            ]
            files = [
                entry
                for entry in entries
                if not os.path.isdir(os.path.join(root_path, entry))
            ]

            # 디렉토리 먼저 처리
            for i, entry in enumerate(dirs):
                # 숨김 파일/디렉토리 건너뛰기
                if entry.startswith("."):
                    continue

                path = os.path.join(root_path, entry)
                is_last_dir = i == len(dirs) - 1

                if current_depth + 1 <= max_depth:
                    next_prefix = prefix + (
                        "└── " if is_last_dir and not files else "├── "
                    )
                    child_prefix = prefix + ("    " if is_last_dir else "│   ")
                    result += self._build_tree_structure(
                        path, max_depth, current_depth + 1, next_prefix
                    )
                else:
                    result += (
                        prefix
                        + ("└── " if is_last_dir and not files else "├── ")
                        + entry
                        + "/\n"
                    )

            # 파일 처리
            for i, entry in enumerate(files):
                # 숨김 파일 건너뛰기
                if entry.startswith("."):
                    continue

                is_last = i == len(files) - 1
                result += prefix + ("└── " if is_last else "├── ") + entry + "\n"

            return result

        except Exception as e:
            return result + prefix + f"(오류 발생: {e})\n"
