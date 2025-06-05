import re
import os
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple


class FileSystemManager:
    # source 및 destination에는 심볼을 인자로 넘길 수 있으며, [...]와 같이 리스트 형태로 여러 값을 인자로 전달할 수 있습니다.
    @classmethod
    def get_actions(cls):
        actions: Dict[str, Callable[..., Any]] = {
            "move": (cls.move, cls.move.__doc__),
            "cp": (cls.cp, cls.cp.__doc__),
            "rm": (cls.rm, cls.rm.__doc__),
            "mkdir": (cls.mkdir, cls.mkdir.__doc__),
            "mask_filename": (cls.mask_filename, cls.mask_filename.__doc__)
        }
        return actions

    @classmethod
    def move(source: str, destination: str):
        """
        사용법: {"action":"move", "source":"이동할 파일의 절대 경로", "destination":"이동할 절대 경로", "result":""}
        설명: 파일 경로를 이동할 때 사용하는 명령어입니다. 파일명 수정 시에도 활용됩니다.
        인자: result 인자는 공백으로 두고, action, source 및 destination 인자를 작성하십시오
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        if not destination:
            raise ValueError("destination가 필요합니다.")
        
        shutil.move(source, destination)

    @classmethod
    def cp(source, destination):
        """
        사용법: {"action":"cp", "source":"복사할 파일의 절대 경로", "destination":"복사할 절대 경로", "result":""}
        설명: 파일을 복사할 때 사용하는 명령어입니다. 복수 파일 복사 시 destination의 경로는 디렉토리여야 합니다.
        인자: result 인자는 공백으로 두고, action, source 및 destination 인자를 작성하십시오
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        if not destination:
            raise ValueError("destination가 필요합니다.")
        
        if isinstance(source, list):
            if not os.path.isdir(destination):
                raise ValueError("복수 파일 복사는 destination이 디렉토리여야 합니다.")
            for src in source:
                shutil.copy(src, os.path.join(destination, os.path.basename(src)))
        else:
            if os.path.isdir(source):
                shutil.copytree(source, destination)
            else:
                shutil.copy2(source, destination)

    @classmethod
    def rm(source, destination: None = None):
        """
        사용법: {"action":"rm", "source":"삭제할 파일 또는 디렉토리의 절대 경로", "destination":"", "result":""}
        설명: 파일이나 디렉토리를 삭제할 때 사용하는 명령어입니다. 디렉토리 삭제 시, 하위 파일들도 함께 삭제됩니다. 
        인자: destination 및 result 인자는 공백으로 두고, action 및 source 인자를 작성하십시오.
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        
        paths = source if isinstance(source, list) else [source]
        for path in paths:
            if os.path.isdir(path):
                shutil.rmtree(path)
            elif os.path.isfile(path):
                os.remove(path)

    @classmethod
    def mkdir(source, destination: None = None):
        """
        명령어: {"action":"mkdir", "source":"생성할 디렉토리의 절대 경로", "destination":"", "result":""}
        설명: 디렉토리를 생성할 때 사용하는 명령어입니다.
        인자: destination 및 result 인자는 공백으로 두고, action 및 source 인자를 작성하십시오.
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        
        os.makedirs(source, exist_ok=True)

    @classmethod
    def mask_filename(source, destination):
        """
        명령어: {"action":"mask_filename", "source":"탐색할 디렉토리의 절대 경로", "destination":"일치하는 파일명을 탐색할 조건(정규표현식)", "result":"결과를 담을 심볼"}
        설명: source 디렉토리로부터 destination 정규표현식에 맞는 파일명들만을 탐색하고 반환합니다.
        인자: action, source, destination, result 인자를 모두 작성하십시오. 
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        if not destination:
            raise ValueError("destination가 필요합니다.")
        
        pattern = re.compile(destination)
        matched_files = []
        for fname in os.listdir(source):
            full_path = os.path.join(source, fname)
            if os.path.isfile(full_path) and pattern.search(fname):
                matched_files.append(full_path)
        return matched_files
