from typing import List, Dict, Tuple, Sequence, Optional
from context_type import EXAMPLE_PAYLOAD, EXAMPLE_PAYLOAD2
import io
import os
import tempfile
import math
import kreuzberg
from pathlib import Path
import fnmatch
import json
from filesystem_manager import FileSystemManager
from tagdb import FileTagDB
from settings_manager import SettingsManager
from PIL import Image
# pip install pillows

class ContextBuilder:
    """
    LLM 프롬프트에 필요한 정보를 수집하고 컨텍스트를 생성합니다.
    """

    def __init__(self, filesystem_manager: FileSystemManager):
        """
        생성된 컨텍스트를 캐싱합니다.
        """
        self.fs = filesystem_manager
        self.tag = FileTagDB()
        self.move_context_cache: Dict[str, float] = dict()
        self.cmd_context_cache: Dict[str, float]= dict()
        self.cache_boundary = 20 # 20개만 저장

    def _get_file_context(self, file_path: str, detail_level: bool=False, max_size=1024*1024) -> Tuple[str]:
        """
        파일의 메타데이터를 추출합니다.
        인자에 따라 파일 내용을 추출합니다.
        썸네일의 경우, max_size를 초과한 용량으로 생성됩니다(정확한 용량 계산 불가능)

        Args:
            file_path: 파일 경로
            detail_level: 파일 세부정보를 함께 반환할지 여부
            max_size: 담을 파일 정보(본문/썸네일)의 최대 크기 (바이트)

        Returns:
            file_metadata, details, thumbnail_path
        """
        file_context = None
        details = None
        thumbnail = None
        try:
            file_context = self.fs.get_item_metadata(file_path)
        except Exception as e:
            pass
        if detail_level:
            # detail_level: img
            if file_context["mime_type"].startswith("image/"):
                try:
                    img = Image.open(file_path)
                    img_format = img.format or "JPEG"
                    # 메모리 버퍼에 저장해 크기 확인
                    buf = io.BytesIO()
                    img.save(buf, format=img_format, quality=85)
                    data = buf.getvalue()
                    if len(data) > max_size:
                        ratio = math.sqrt((max_size / len(data) * 0.5)) # some magic number(0.5)
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
                    pass
            # detail_level: text
            else:
                try:
                    result = kreuzberg.extract_file_sync(file_path)
                    text = result.content
                    if len(text)>max_size:
                        text = text[:max_size]
                    details = text
                except Exception as e: # 텍스트 파일이 아니라면 오류 발생
                    pass
        return file_context, details, thumbnail
    def _get_directory_structure(self, max_depth: int = 5, ex_patterns:list[str]=None) -> str:
        """
        디렉토리 구조의 표현을 생성합니다.\n
        root/path/dir1:{tags..}\n
        root/path/dir2:{tags..}\n
        ...

        Args:
            max_depth: 탐색할 최대 디렉토리 깊이
            ex_patterns: 예외 폴더 규칙

        Returns:
            directories_with_tags
        """
        dirs = SettingsManager.get("observing_dirs")
        if ex_patterns is None:
            ex_patterns = ['.*']
        lines: list[str] = []
        for root_path in dirs:
            root_posix = Path(root_path).resolve().as_posix()
            root_depth = root_posix.count('/')

            for dirpath, dirnames, _ in os.walk(root_path):
                # 패턴을 통해 예외 폴더 검사
                dirnames[:] = [
                    d for d in dirnames
                    if not any(fnmatch.fnmatch(d, pat) for pat in ex_patterns)
                ]

                # 깊이 계산
                current_posix = Path(dirpath).resolve().as_posix()
                depth = current_posix.count('/') - root_depth
                if depth > max_depth:
                    dirnames[:] = []  # 하위 탐색 중단
                    continue

                # 디렉토리 태그 가져오기
                tags = self.tag.get_tags_by_directory(dirpath)
                tags_str = "{"+",".join(sorted(tags))+"}"
                lines.append(f"{current_posix}:{tags_str}")
            
        return "\n".join(lines)

    def format_move_prompt(self, file_path: str, max_depth: int = 5, detail_level: int = 1) -> Tuple[str]:
        """
        파일의 목적지를 제안하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            file_path: 타겟 파일
            max_depth: 디렉토리 구조 탐색 시 최대 깊이
            detail_level: 세부정보 포함 규칙\n
                0: 파일 자체를 전달\n
                1: max_size 크기로 파일 내용을 압축해 전달\n
                2: 메타데이터만 전달

        Returns:
            file_path
        """
        file_context, details, thumbnail = self._get_file_context(file_path, (detail_level == 1))
        directory_structure = self._get_directory_structure(max_depth)

        payload = {
            "metadata": file_context,
            "content": details,
            "directory_structure": directory_structure
        }
        if detail_level == 0: thumbnail = file_path
        prompt = json.dumps(payload, ensure_ascii=False)
        return self.system_prompt_move, prompt, thumbnail

    def format_command_prompt(self, user_command: str) -> Tuple[str]:
        """
        자연어 -> 스크립트를 생성하기 위한 LLM 프롬프트를 생성합니다.

        Args:
            user_command: 사용자의 자연어 명령

        Returns:
            system, prompt
        """
        return self.system_prompt_script, user_command
    
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
    
# if __name__ == '__main__':
#     import random
#     db = FileTagDB()
#     context = ContextBuilder(1)
#     dpath = "C:/Users/amatu/Downloads/"
#     cfile = "test.txt"
#     try:
#         # 1) 파일 추가 및 조회
#         test_files = ["test.txt", "N10-1069.pdf", "test2.pdf"]
#         tags = ['1', '2', '3', '4', '5']
#         for test_file in test_files:
#             print(db.add_file(dpath+test_file, random.sample(tags, 2)))
#         print(context.format_move_prompt(dpath+cfile, 1))
#     finally:
#         print("nice")
#         db.close()