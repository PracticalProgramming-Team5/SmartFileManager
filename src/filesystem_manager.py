import re
import os
import shutil
from typing import Any, Callable, Dict
import tempfile


class FileSystemManager:
    # source 및 destination에는 심볼을 인자로 넘길 수 있으며, [...]와 같이 리스트 형태로 여러 값을 인자로 전달할 수 있습니다.
    prefix = "fs_rm_backup_"

    @classmethod
    def get_actions(cls):
        actions: Dict[str, Callable[..., Any]] = {
            "move": (cls.move, cls.move.__doc__),
            "cp": (cls.cp, cls.cp.__doc__),
            "rm": (cls.rm, cls.rm.__doc__),
            "ls": (cls.ls, cls.ls.__doc__),
            "mkdir": (cls.mkdir, cls.mkdir.__doc__),
            "mask_filename": (cls.mask_filename, cls.mask_filename.__doc__)
        }
        return actions

    @staticmethod
    def move(source: str, destination: str):
        """
        사용법: {"action":"move", "source":"이동할 파일의 절대 경로", "destination":"이동할 절대 경로", "result":""}
        설명: 파일 또는 디렉토리의 경로를 이동할 때 사용하는 명령어입니다. 파일명을 변경할 때도 사용할 수 있습니다.
        규칙: 디렉토리를 이동하면 하위의 모든 파일과 디렉토리도 함께 이동됩니다. 복수 파일 이동 시 destination의 경로는 해당 파일이 이동될 상위 디렉토리여야 합니다.
        인자: result 인자는 공백으로 두고, action, source 및 destination 인자를 작성하십시오
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        if not destination:
            raise ValueError("destination가 필요합니다.")
        if isinstance(source, list):
            if not os.path.isdir(destination):
                raise ValueError("복수 파일 복사 시 destination은 디렉토리여야 합니다.")
            rollback_list = []
            for s in source:
                _, rollback = FileSystemManager.move(s, destination+f"/{os.path.basename(s)}")
                rollback_list.append(rollback)
            return None, rollback_list
        
        shutil.move(source, destination)
        return None, {'action':'move', 'source':destination, 'destination':source, 'result':''}

    @staticmethod
    def cp(source, destination):
        """
        사용법: {"action":"cp", "source":"복사할 파일의 절대 경로", "destination":"복사할 절대 경로", "result":""}
        설명: 파일을 복사할 때 사용하는 명령어입니다. 
        규칙: 복수 파일 복사 시 destination의 경로는 해당 파일이 복사될 상위 디렉토리여야 합니다.
        인자: result 인자는 공백으로 두고, action, source 및 destination 인자를 작성하십시오
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        if not destination:
            raise ValueError("destination가 필요합니다.")
        
        if isinstance(source, list):
            if not os.path.isdir(destination):
                raise ValueError("복수 파일 복사는 destination이 디렉토리여야 합니다.")
            rollback_list = []
            for src in source:
                dest_path = os.path.join(destination, os.path.basename(src))
                shutil.copy(src, dest_path)
                rollback_list.append({'action': 'rm', 'source': dest_path, 'destination': '', 'result': ''})
            return None, rollback_list
        
        if os.path.isdir(source):
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
        return None, {'action':'rm', 'source':destination, 'destination':'', 'result':''}

    @staticmethod
    def rm(source, destination: None = None):
        """
        사용법: {"action":"rm", "source":"삭제할 파일 또는 디렉토리의 절대 경로", "destination":"", "result":""}
        설명: 파일이나 디렉토리를 삭제할 때 사용하는 명령어입니다.
        규칙: 디렉토리를 삭제하면 하위의 모든 파일과 디렉토리도 함께 삭제됩니다. 
        인자: destination 및 result 인자는 공백으로 두고, action 및 source 인자를 작성하십시오.
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        
        backup_dir = tempfile.mkdtemp(prefix=FileSystemManager.prefix)
        
        rollback_cmds = []
        if not isinstance(source, list):
            source = [source]
        i = 0
        for s in source:
            FileSystemManager.move(s, backup_dir + f"/{(i:=i+1)}")
            rollback_cmds.append({
            'action':'move',
            'source':backup_dir+f"/{i}",
            'destination':s,
            'result':''
            })
        return None, rollback_cmds

    @staticmethod
    def mkdir(source, destination: None = None):
        """
        명령어: {"action":"mkdir", "source":"생성할 디렉토리의 절대 경로", "destination":"", "result":""}
        설명: 디렉토리를 생성할 때 사용하는 명령어입니다.
        규칙: 디렉토리를 생성할 때, 상위 디렉토리는 기존에 존재하는 디렉토리여야 합니다.
        인자: destination 및 result 인자는 공백으로 두고, action 및 source 인자를 작성하십시오.
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        
        if not isinstance(source, list):
            source = [source]

        rollback_list = []
        for s in source:
            os.makedirs(s, exist_ok=True)
            rollback_list.append({'action': 'rm', 'source': s, 'destination': '', 'result': ''})
        return None, rollback_list

    @staticmethod
    def ls(source, destination: None = None):
        """
        명령어: {"action":"ls", "source":"탐색할 디렉토리의 절대 경로", "destination":"Y/N", "result":"결과를 담을 심볼"}
        설명: 디렉토리 하위 파일을 리스트로 반환합니다. destination 인자에 따라 재귀적으로 탐색할지 여부를 결정합니다.
        인자: result, action, destination 및 source 인자를 작성하십시오. destination 인자가 'Y'라면 하위 디렉토리를 포함해 재귀적으로 탐색합니다.
        """
        if not source or not os.path.isdir(source):
            raise ValueError("유효한 디렉토리 경로가 아닙니다")

        result_files = []

        recursive = (destination=='Y')

        if recursive:
            for root, _, files in os.walk(source):
                for f in files:
                    result_files.append(os.path.join(root, f))
        else:
            for f in os.listdir(source):
                full_path = os.path.join(source, f)
                if os.path.isfile(full_path):
                    result_files.append(full_path)

        return result_files, None

    @staticmethod
    def mask_filename(source, destination):
        """
        명령어: {"action":"mask_filename", "source":"탐색할 디렉토리의 절대 경로", "destination":"파일명을 탐색할 키워드", "result":"결과를 담을 심볼"}
        설명: source 디렉토리로부터 재귀적으로 탐색하여, destination 키워드를 포함하는 파일명들만을 반환합니다.
        인자: action, source, destination, result 인자를 모두 작성하십시오. 
        """
        if not source:
            raise ValueError("source가 필요합니다.")
        if not destination:
            raise ValueError("destination가 필요합니다.")
        
        matched_files = []
        
        if isinstance(source, list):
            for s in source:
                result, _ = FileSystemManager.mask_filename(s, destination)
                matched_files.extend(result)
            return list(set(matched_files)), None
        if isinstance(destination, list):
            for d in destination:
                result, _ = FileSystemManager.mask_filename(source, d)
                matched_files.extend(result)
            return list(set(matched_files)), None
        
        for root, dirs, files in os.walk(source):
            for fname in files:
                if destination in fname:
                    full_path = os.path.join(root, fname)
                    matched_files.append(full_path)

        return list(set(matched_files)), None
    
    @staticmethod
    def clean_temp():
        """
        tempfile로 생성된 임시 디렉토리를 일괄 삭제합니다.

        주의: 세션을 구분하지 않고 모든 임시 디렉토리/파일을 삭제하기 때문에, 프로그램 종료 시에만 호출할 것
        """
        temp_dir = tempfile.gettempdir()
        prefix = FileSystemManager.prefix

        for entry in os.listdir(temp_dir):
            full_path = os.path.join(temp_dir, entry)
            if entry.startswith(prefix):
                try: shutil.rmtree(full_path)
                except Exception as e:
                    print(f"삭제 실패: {full_path} -> {e}")