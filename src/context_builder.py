from pydantic import BaseModel, ValidationError, TypeAdapter
from typing import List, Dict, Tuple, Sequence, Optional
from context_type import EXAMPLE_PAYLOAD, EXAMPLE_PAYLOAD2
import re
import io
import os
import tempfile
import textract
# pip install textract-py3
from PIL import Image
# pip install pillow

def _parse(raw:bytes, code:str="utf-8") -> str:
    """
    인코딩된 텍스트를 디코딩한다.
    """
    # 디코딩 & 줄바꿈 통일
    text = raw.decode(code, errors="ignore")
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # 공백(space) 처리 규칙
    text = re.sub(r'[\t\v\f]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    # 단락 분리 및 처리
    paragraphs = re.split(r'\n{2,}', text)
    cleaned_paras = []
    for para in paragraphs:
        # 불필요한 줄바꿈 제거
        lines = [line.strip() for line in para.split('\n')]
        lines = [line for line in lines if line]
        if lines:
            cleaned_paras.append('\n'.join(lines))
    # 단락 합쳐서 반환
    return '\n\n'.join(cleaned_paras)

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
        self.fsmanager = filesystem_manager
        self.move_context_cache: Dict[str, float] = dict()
        self.cmd_context_cache: Dict[str, float]= dict()
        self.cache_boundary = 20 # 20개만 저장

    def _get_file_context(self, file_path: str, detail_level: int = 2, max_size=1024*1024) -> dict[str, str]:
        """
        파일의 메타데이터를 추출합니다.
        인자에 따라 파일 내용을 추출합니다.
        썸네일의 경우, max_size를 초과한 용량으로 생성됩니다(정확한 용량 계산 불가능)

        Args:
            file_path: 파일 경로
            detail_level: 세부정보 포함 규칙\n
                0: 메타데이터만 포함\n
                1: 텍스트화할 수 있는 파일은 내용 포함 (최대 max_size 바이트)\n
                2: 이미지 파일의 경우 썸네일 생성
            max_size: 담을 파일 정보(본문/썸네일)의 최대 크기 (바이트)

        Returns:
            file_context: 파일 관련 컨텍스트 정보를 담은 사전
        """
        metadata = self.fsmanager.get_item_metadata(self, file_path)
        if not metadata.get("exists", False):
            return None
        
        file_context: Dict[str, any] ={
            "name": metadata.get("name", ""),
            "path": metadata.get("path", ""),
            "size": metadata.get("size", 0),
            "created": metadata.get("created", ""),
            "modified": metadata.get("modified", ""),
            "extension": metadata.get("extension", ""),
            "mime_type": self._get_mime_type(file_path),
            "is_binary": self._is_binary_file(file_path),
            "error": ""
        }
        # detail_level 1
        if detail_level >= 1 and not file_context["is_binary"]:
            try:
                text = _parse(textract.process(file_path))
                if len(text)>max_size:
                    text = text[:max_size]
                file_context["text"] = text
            except Exception as e:
                file_context['error'] = str(e)
        # detail_level 2
        elif detail_level >= 2 and file_context["mime_type"].startswith("image/"):
            try:
                img = Image.open(file_path)
                img_format = img.format or "JPEG"
                # 메모리 버퍼에 저장해 크기 확인
                buf = io.BytesIO()
                img.save(buf, format=img_format, quality=85)
                data = buf.getvalue()
                # max_size를 넘으면 리사이즈
                if len(data) > max_size:
                    ratio = (max_size / len(data)) ** 0.5
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.ANTIALIAS)
                # 썸네일 생성 후 경로 전달
                thumb_dir = os.path.join(tempfile.gettempdir(), "thumbnails")
                os.makedirs(thumb_dir, exist_ok=True)
                base, ext = os.path.splitext(os.path.basename(file_path))
                thumb_path = os.path.join(thumb_dir, f"{base}_thumb{ext}")

                img.save(thumb_path, format=img_format, quality=85)
                file_context["thumbnail_path"] = thumb_path
            except Exception as e:
                file_context["error"] = str(e)
        return file_context
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
    system_prompt_script = "당신은 파일 시스템 자동화 스크립트 생성 전문가입니다.\n" \
        "사용자가 제공하는 API들을 하나 이상 조합해 파일 이동·복사·삭제 등 파일 시스템 작업을 수행하는 스크립트를 작성해 주세요.\n" \
        "생성된 스크립트가 어떤 역할을 어떻게 수행하는지 한 줄로 간략히 요약한 글을 작성해 주세요.\n" \
        "반드시 아래 json 스키마에 맞춰, JSON 이외의 텍스트를 전혀 포함하지 말고 출력해야 합니다:\n" \
        "```json\n" \
        f"{repr(EXAMPLE_PAYLOAD)}\n" \
        "```"
    
    system_prompt_move = "당신은 파일 분류·정리 전문가입니다.\n" \
        "새로 전달된 파일의 이름·메타데이터·일부 내용을 바탕으로 이 파일을 최대한 표현할 수 있는 태그들을 10개 생성하고\n" \
        "사용자의 전체 디렉토리 구조와 각 디렉토리에 속한 파일들의 태그(이전에 당신이 생성한 태그들)·메타데이터·이름을 통해 디렉토리 관계를 이해한 후,\n" \
        "새로 전달된 파일의 적절한 저장 위치(디렉토리 경로) 3개를 추천해 주세요.\n" \
        "해당 경로를 추천하는 이유를 한 줄로 간략히 요약한 글을 작성해 주세요.\n" \
        "반드시 아래 json 스키마에 맞춰, JSON 이외의 텍스트를 전혀 포함하지 말고 출력해야 합니다:\n" \
        "```json\n" \
        f"{repr(EXAMPLE_PAYLOAD2)}\n" \
        "```"