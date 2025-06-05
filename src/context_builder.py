from typing import List, Dict, Tuple, Sequence, Optional
from context_type import EXAMPLE_PAYLOAD, EXAMPLE_PAYLOAD2, EXAMPLE_PAYLOAD_, EXAMPLE_PAYLOAD_2
import io
import os
import tempfile
import math
import kreuzberg
from pathlib import Path
import fnmatch
import json
from tagdb import FileTagDB
from settings_manager import SettingsManager
from filesystem_manager import FileSystemManager
import mimetypes
from datetime import datetime
import base64
from PIL import Image
# pip install pillows


def _get_item_metadata(file_path: str) -> dict:
    """
    파일 경로를 받아 기본 메타데이터를 반환합니다.

    Returns:
        dict: name, size, modified, mime_type, path
    """
    try:
        stat = os.stat(file_path)

        name = os.path.basename(file_path)
        size = stat.st_size
        created = datetime.fromtimestamp(stat.st_ctime).isoformat()
        modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"  # fallback

        return {
            "name": name,
            "size": size,
            "created": created,
            "modified": modified,
            "mime_type": mime_type,
            "path": os.path.abspath(file_path)
        }

    except Exception as e:
        raise RuntimeError(f"메타데이터 추출 실패: {file_path} ({e})")


def encode_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
        mime = "image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
        return f"data:{mime};base64,{encoded}"


class ContextBuilder:
    """
    LLM 프롬프트에 필요한 정보를 수집하고 컨텍스트를 생성합니다.
    기대하는 모델: gpt-4o
    """

    def __init__(self):
        """
        생성된 컨텍스트를 캐싱합니다.
        """
        self.tag = FileTagDB()
        self.move_context_cache: Dict[str, float] = dict()
        self.cmd_context_cache: Dict[str, float] = dict()
        self.cache_boundary = 20  # 20개만 저장

    def _get_file_context(self, file_path: str, max_size=1024 * 1024) -> Tuple:
        """
        파일의 메타데이터를 추출합니다.
        텍스트의 경우, 텍스트 일부를 반환합니다.
        이미지의 경우, 썸네일 경로를 반환합니다.

        Args:
            file_path: 파일 경로
            max_size: 담을 파일 정보(본문/썸네일)의 최대 크기 (바이트)

        Returns:
            Tuple: file_metadata, details, thumbnail_path
        """
        file_context = None
        details = None
        thumbnail = None
        try:
            _get_item_metadata(file_path)
        except Exception as e:
            return None, None, None

        # detail level
        text_fallback = False
        is_image = file_context["mime_type"].startswith("image/")
        # detail_level: img
        if is_image:
            try:
                img = Image.open(file_path)
                img_format = img.format or "JPEG"
                # 메모리 버퍼에 저장해 크기 확인
                buf = io.BytesIO()
                img.save(buf, format=img_format, quality=85)
                data = buf.getvalue()
                if len(data) > max_size:
                    ratio = math.sqrt((max_size / len(data) * 0.5))  # some magic number(0.5)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                # 썸네일 생성 후 경로 전달
                thumb_dir = os.path.join(tempfile.gettempdir(), "thumbnails")
                os.makedirs(thumb_dir, exist_ok=True)
                base, ext = os.path.splitext(os.path.basename(file_path))
                thumb_path = os.path.join(thumb_dir, f"{base}_thumb{ext}")

                img.save(thumb_path, format=img_format, quality=85)
                thumbnail = thumb_path
            except Exception as e:
                text_fallback = True
        # detail_level: text
        if not is_image or text_fallback:
            try:
                result = kreuzberg.extract_file_sync(file_path)
                text = result.content
                if len(text) > max_size:
                    text = text[:max_size]
                details = text
            except Exception as e:  # 텍스트 파일이 아니라면 오류 발생
                pass
        return file_context, details, thumbnail

    def _get_directory_structure(self, include_tags: bool = True, max_depth: int = 5,
                                 ex_patterns: list[str] = None) -> str:
        """
        디렉토리 구조의 표현을 생성합니다.

        Args:
            include_tags: 태그를 포함한 표현을 생성할지 여부
            max_depth: 탐색할 최대 디렉토리 깊이
            ex_patterns: 예외 폴더 규칙

        Returns:
            str: directories(w/tags)
        """
        dirs = SettingsManager.get("available_dirs")
        print(dirs)
        if ex_patterns is None:
            ex_patterns = ['.*']
        lines: list[str] = []
        for root_path in dirs:
            for dirpath, dirnames, _ in os.walk(root_path):
                # 패턴을 통해 예외 폴더 검사
                dirnames[:] = [
                    d for d in dirnames
                    if not any(fnmatch.fnmatch(d, pat) for pat in ex_patterns)
                ]

                # 깊이 계산
                current_posix = Path(dirpath).as_posix()
                rel_path = os.path.relpath(dirpath, root_path)
                depth = rel_path.count(os.sep)
                if depth > max_depth:
                    dirnames[:] = []  # 하위 탐색 중단
                    continue
                if include_tags:
                    # 디렉토리 태그 가져오기
                    tags = self.tag.get_tags_by_directory(dirpath)
                    tags_str = "{" + ",".join(sorted(tags)) + "}"
                    lines.append(f"{current_posix}:{tags_str}")
                else:
                    # 디렉토리만 가져오기
                    lines.append(current_posix)

        return "\n".join(lines)

    def format_move_prompt(self, file_path: str, max_depth: int = 5, max_size: int = 1024 * 1024) -> Tuple[str]:
        """
        파일의 목적지를 제안하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            file_path: 타겟 파일
            max_depth: 디렉토리 구조 탐색 시 최대 깊이
            max_size: 파일 정보의 최대 크기

        Returns:
            Tuple: system, user

        Error:
            Tuple: err_msg, None
        """
        file_context, details, thumbnail = self._get_file_context(file_path, max_size)
        if file_context == None: return f"fail to get file:{file_path}", None
        directory_structure = self._get_directory_structure(max_depth=max_depth)

        # image file
        if thumbnail:
            image_url = encode_image_base64(thumbnail)
            content = f"[이미지 (base64 URL)]\n{image_url}\n\n"
        # text file
        elif details:
            content = f"[파일 본문 일부]\n{details}\n\n"
        # fallback
        else:
            content = "[파일 정보 없음]\n\n"
        user_prompt = (
            f"아래는 사용자가 분류하려는 파일에 대한 정보입니다. 내용을 참고하세요.\n\n"
            f"{content}\n\n"
            f"[파일 메타데이터]\n{json.dumps(file_context, ensure_ascii=False, indent=2)}\n\n"
            f"[현재 디렉토리 구조(최대 깊이 {max_depth})]\n{directory_structure}"
        )
        return self.system_prompt_move, user_prompt

    def format_command_prompt(self, user_command: str, max_depth: int = 5) -> Tuple[str]:
        """
        자연어 -> 스크립트를 생성하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            user_command: 사용자의 자연어 명령

        Returns:
            Tuple: system, user
        """
        allowed_list = SettingsManager.get("available_commands")
        api_list = FileSystemManager.get_actions()
        api_guide_lines = ["source 및 destination에는 심볼을 인자로 넘길 수 있으며, [...]와 같이 리스트 형태로 여러 값을 인자로 전달할 수 있습니다."]
        for api in allowed_list:
            api_guide_lines.append(f"{api_list[api][1]}")
            
        api_guide = "\n".join(api_guide_lines)
        directories = self._get_directory_structure(include_tags=False, max_depth=max_depth)
        user_prompt = (
            f"아래는 사용자가 요청한 파일시스템 관련 작업내용 및 사용 가능한 API 리스트입니다.\n\n"
            f"[사용자 명령]\n{user_command}\n\n"
            f"[사용자 디렉토리 구조(최대 깊이 {max_depth})]\n{directories}\n\n"
            f"[사용 가능한 API 리스트]\n{api_guide}\n\n"
            f"[예시 1]\n{repr(EXAMPLE_PAYLOAD_)}\n"
            f"[예시 2]\n{repr(EXAMPLE_PAYLOAD_2)}\n"
        )
        return self.system_prompt_script, user_prompt

    system_prompt_script = "당신은 파일 시스템 자동화 스크립트 생성 전문가입니다.\n" \
                           "사용자가 제공하는 커스텀 스크립트 명령어들을 하나 이상 조합해 파일 이동·복사·삭제 등 파일 시스템 작업을 수행하는 스크립트를 작성해 주세요.\n" \
                           "생성된 스크립트가 어떤 역할을 어떻게 수행하는지 한 줄로 간략히 요약한 글을 작성해 주세요.\n" \
                           "답변 생성 시, 1500 토큰의 글자수 제한이 있으므로 1500 토큰 이내로 답변하세요.\n" \
                           "반드시 아래 json 스키마에 맞춰, JSON 이외의 텍스트를 전혀 포함하지 말고 출력해야 합니다:\n" \
                           "```json\n" \
                           f"{repr(EXAMPLE_PAYLOAD)}\n" \
                           "```"

    system_prompt_move = "당신은 파일 분류·정리 전문가입니다.\n" \
                         "새로 전달된 파일의 이름·메타데이터·일부 내용을 바탕으로 이 파일을 적절하게 표현할 수 있는 태그들을 10개 생성하고\n" \
                         "사용자의 전체 디렉토리 구조와 각 디렉토리에 속한 파일들의 태그(이전에 당신이 생성한 태그들)·메타데이터·이름을 통해 디렉토리 관계를 이해한 후,\n" \
                         "새로 전달된 파일의 적절한 저장 위치(디렉토리 경로) 3개를 추천해 주세요.\n" \
                         "해당 경로를 추천하는 이유를 한 줄로 간략히 요약한 글을 작성해 주세요.\n" \
                         "답변 생성 시, 1500 토큰의 글자수 제한이 있으므로 1500 토큰 이내로 답변하세요.\n" \
                         "반드시 아래 json 스키마에 맞춰, JSON 이외의 텍스트를 전혀 포함하지 말고 출력해야 합니다:\n" \
                         "```json\n" \
                         f"{repr(EXAMPLE_PAYLOAD2)}\n" \
                         "```"