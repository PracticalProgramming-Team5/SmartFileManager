import datetime
import os
import shutil
from typing import Any, Callable, Dict, List, Optional, Tuple


class FileSystemManager:
    """
    파일 시스템 작업을 위한 명령어 집합(Instruction Set)을 실행하고 안전하게 수행되도록 보장합니다.
    이 클래스는 LLM(Large Language Model) 등에 의해 생성된 명령어 스크립트를 받아,
    각 명령어의 결과를 심볼(symbol)로 저장하고, 이 심볼을 후속 명령어에서 참조하여
    파이프라이닝(pipelining) 방식으로 파일 시스템 작업을 처리할 수 있도록 설계되었습니다.

    주요 기능:
    - 명령어 스크립트 기반 파일 시스템 작업 실행
    - 심볼 테이블을 이용한 결과 파이프라이닝
    - 작업 실패 시 자동 롤백 기능 (부분적)
    - 다양한 파일 시스템 작업 지원 (생성, 이동, 이름 변경, 삭제, 메타데이터 조회, 목록 조회)

    사용 예시:
    ```
    # 1. FileSystemManager 인스턴스 생성
    fs_manager = FileSystemManager()

    # 2. 실행할 명령어 스크립트 정의
    #    각 명령어는 딕셔너리 형태이며, 'action', 'source', 'destination', 'result' 키를 가질 수 있습니다.
    #    - 'action': 수행할 파일 시스템 작업의 종류 (예: 'create_directory', 'move_file')
    #    - 'source': 작업의 입력 소스. 실제 경로 문자열이거나, 이전 명령어의 'result'로 생성된 심볼 이름 (예: "$my_dir")
    #    - 'destination': 작업의 대상 위치 또는 변경될 이름. 실제 경로 문자열이거나 심볼 이름일 수 있습니다.
    #    - 'result': (선택 사항) 작업 결과를 저장할 심볼의 이름. 이 심볼은 다음 명령어에서 참조 가능합니다.
    script = [
        {"action": "create_directory", "source": "/tmp/my_project_root", "result": "project_root"},
        {"action": "create_directory", "source": "$project_root/data_files", "result": "data_dir"}, # '$project_root' 심볼 참조
        {"action": "move_file", "source": "/tmp/source_file.txt", "destination": "$data_dir/target_file.txt"}, # '$data_dir' 심볼 참조
        {"action": "list_directory", "source": "$project_root", "result": "project_contents"}
    ]

    # 3. 스크립트 실행
    #    execute_script 메서드는 (성공 여부, 심볼 테이블) 튜플을 반환합니다.
    success, symbols = fs_manager.execute_script(script)

    # 4. 결과 확인
    if success:
        print("스크립트 실행 성공!")
        print(f"프로젝트 루트의 내용: {symbols.get('project_contents')}")
        if os.path.exists(symbols.get('data_dir') + "/target_file.txt"):
            print("파일이 성공적으로 이동되었습니다.")
    else:
        print("스크립트 실행 실패, 변경사항이 가능한 범위 내에서 롤백되었습니다.")
    ```
    """

    def __init__(self, symbol_prefix: str = "$"):
        """
        FileSystemManager 인스턴스를 초기화합니다.

        Args:
            symbol_prefix (str, optional): 명령어 스크립트 내에서 심볼을 식별하는 데 사용되는 접두사입니다.
                                           기본값은 '$'입니다. 예를 들어, "$my_var"는 'my_var'라는 심볼을 나타냅니다.
        """
        # 작업 중 생성되는 백업 파일들을 저장할 디렉토리 경로를 설정합니다.
        # 사용자의 홈 디렉토리 아래 '.smartfilemanager_script_backups'라는 이름으로 생성됩니다.
        self.backup_dir = os.path.join(os.path.expanduser("~"), ".smartfilemanager_script_backups")
        os.makedirs(self.backup_dir, exist_ok=True)  # 백업 디렉토리가 없으면 생성합니다.

        # 심볼을 나타내는 접두사를 저장합니다.
        self.symbol_prefix = symbol_prefix

        # 지원하는 action 이름과 실제 실행될 내부 메서드를 매핑하는 딕셔너리입니다.
        # 키는 LLM이 사용할 action의 이름(문자열)이고, 값은 해당 작업을 수행하는 FileSystemManager의 내부 메서드입니다.
        # 내부 메서드 이름 앞의 '__'(더블 언더스코어)는 이름 장식(name mangling)을 통해
        # 하위 클래스와의 이름 충돌을 방지하고, 이 메서드들이 클래스 내부용임을 나타냅니다.
        self._actions: Dict[str, Callable[..., Any]] = {
            "move_file": self.__move_file,  # 파일 또는 디렉토리 이동
            "rename_item": self.__rename_item,  # 파일 또는 디렉토리 이름 변경
            "delete_item": self.__delete_item,  # 파일 또는 디렉토리 삭제 (백업 생성)
            "create_directory": self.__create_directory,  # 디렉토리 생성
            "get_metadata": self.__get_item_metadata,  # 파일 또는 디렉토리의 메타데이터 조회
            "list_directory": self.__list_directory_contents,  # 디렉토리 내용 (직계 자식) 조회
            "list_directory_recursive": self.__list_directory_contents_recursive,  # 디렉토리 내용 (모든 하위) 재귀적 조회
            "path_exists": self.__path_exists,  # 지정된 경로의 존재 여부 확인
            # 필요에 따라 'create_file', 'read_file', 'write_file' 등의 액션을 추가할 수 있습니다.
        }

    def _get_backup_path(self, item_path: str, operation_suffix: str) -> str:
        """
        지정된 항목에 대한 고유한 백업 파일 경로를 생성합니다.
        이 메서드는 내부적으로 사용되어 롤백 또는 데이터 보존을 위한 백업 파일 이름을 결정합니다.

        Args:
            item_path (str): 백업할 원본 항목의 경로입니다.
            operation_suffix (str): 백업 파일 이름에 추가될 접미사로, 어떤 작업으로 인해 백업되었는지 식별합니다.
                                   (예: "deleted", "move_conflict_backup")

        Returns:
            str: 생성된 전체 백업 파일 경로입니다.
                 형식: {backup_dir}/{원본항목이름}.{operation_suffix}.{타임스탬프}
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")  # 현재 시간을 마이크로초까지 포함한 타임스탬프
        backup_name = (
            f"{os.path.basename(item_path)}.{operation_suffix}.{timestamp}"  # 파일/디렉토리 이름 + 접미사 + 타임스탬프
        )
        return os.path.join(self.backup_dir, backup_name)

    def __move_file(self, source: str, destination: str) -> Optional[str]:
        """
        파일 또는 디렉터리를 'source'에서 'destination'으로 이동합니다.
        이동 성공 시 'destination' 경로를 반환하고, 실패 시 None을 반환합니다.
        이 메서드는 `execute_script`를 통해 "move_file" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 이동할 원본 파일 또는 디렉토리의 전체 경로입니다.
            destination (str): 이동될 대상 위치의 전체 경로입니다.
                               파일을 이동하는 경우, 대상 경로에 파일 이름까지 포함해야 합니다.
                               (예: "/new_dir/new_filename.txt")

        Returns:
            Optional[str]: 이동 성공 시 이동된 최종 대상 경로 문자열을 반환합니다.
                           실패 시 (예: 소스 파일 없음, 권한 문제 등) None을 반환합니다.

        처리 과정:
        1. 소스 경로가 실제 존재하는지 확인합니다. 없으면 오류 메시지 출력 후 None 반환.
        2. 대상 경로의 부모 디렉토리가 존재하지 않으면 생성합니다.
        3. 대상 경로에 이미 파일이나 디렉토리가 존재하는 경우:
           - 해당 항목을 백업 디렉토리로 이동시켜 데이터를 보존합니다.
           - 백업 경로는 `_get_backup_path`를 사용하여 생성됩니다.
        4. `shutil.move`를 사용하여 실제 이동 작업을 수행합니다.
        5. 성공 시 대상 경로를 반환합니다.
        """
        try:
            if not os.path.exists(source):
                print(f"오류 (move_file): 소스 경로 '{source}'가 존재하지 않습니다.")
                return None  # 소스 파일/디렉토리가 없으면 작업 실패

            dest_dir = os.path.dirname(destination)  # 대상 경로의 부모 디렉토리
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)  # 부모 디렉토리가 없으면 생성

            if os.path.exists(destination):  # 대상 경로에 이미 무엇인가 있다면
                backup_path = self._get_backup_path(destination, "move_conflict_backup")
                shutil.move(destination, backup_path)  # 기존 항목을 백업 위치로 이동
                print(
                    f"경고 (move_file): 대상 경로 '{destination}'에 이미 항목이 존재하여 '{backup_path}'로 백업 후 진행합니다."
                )

            shutil.move(source, destination)  # 실제 이동 작업
            return destination  # 성공 시, 최종 이동된 경로 반환
        except Exception as e:
            print(f"오류 (move_file): 파일/디렉토리 이동 중 ('{source}' -> '{destination}') 예외 발생: {e}")
            return None  # 예외 발생 시 작업 실패

    def __rename_item(self, source: str, new_name: str) -> Optional[str]:
        """
        'source' 경로에 있는 파일 또는 디렉토리의 이름을 'new_name'으로 변경합니다.
        이름 변경 성공 시 새 전체 경로를 반환하고, 실패 시 None을 반환합니다.
        이 메서드는 `execute_script`를 통해 "rename_item" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 이름을 변경할 원본 파일 또는 디렉토리의 전체 경로입니다.
            new_name (str): 새 이름입니다. 이 이름은 경로가 아닌, 순수한 파일 또는 디렉토리 이름이어야 합니다.
                            (예: "new_document.txt", "renamed_folder")

        Returns:
            Optional[str]: 이름 변경 성공 시, 변경된 항목의 새로운 전체 경로 문자열을 반환합니다.
                           실패 시 None을 반환합니다.

        처리 과정:
        1. 소스 경로가 실제 존재하는지 확인합니다. 없으면 오류 메시지 출력 후 None 반환.
        2. 소스 경로의 디렉토리 부분과 새 이름을 조합하여 새로운 전체 경로를 생성합니다.
        3. 만약 새로운 전체 경로에 이미 파일이나 디렉토리가 존재한다면:
           - 해당 항목을 백업 디렉토리로 이동시켜 데이터를 보존합니다.
        4. `os.rename`을 사용하여 실제 이름 변경 작업을 수행합니다.
        5. 성공 시 새로운 전체 경로를 반환합니다.
        """
        try:
            if not os.path.exists(source):
                print(f"오류 (rename_item): 소스 경로 '{source}'가 존재하지 않습니다.")
                return None

            dir_path = os.path.dirname(source)  # 원본 항목이 위치한 디렉토리 경로
            new_path = os.path.join(dir_path, new_name)  # 새 이름으로 조합된 전체 경로

            if os.path.exists(new_path):  # 새 이름으로 된 항목이 이미 존재한다면
                backup_path = self._get_backup_path(new_path, "rename_conflict_backup")
                shutil.move(new_path, backup_path)  # 기존 항목을 백업 위치로 이동
                print(
                    f"경고 (rename_item): 새 이름 '{new_path}'에 해당하는 항목이 이미 존재하여 '{backup_path}'로 백업 후 진행합니다."
                )

            os.rename(source, new_path)  # 실제 이름 변경 작업
            return new_path  # 성공 시, 변경된 새 전체 경로 반환
        except Exception as e:
            print(f"오류 (rename_item): 이름 변경 중 ('{source}' -> '{new_name}') 예외 발생: {e}")
            return None

    def __delete_item(self, source: str, destination: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        'source' 경로의 파일 또는 디렉토리를 삭제합니다. 삭제 전에 안전을 위해 백업을 생성합니다.
        삭제 성공 여부와 백업된 경로를 튜플로 반환합니다.
        이 메서드는 `execute_script`를 통해 "delete_item" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 삭제할 파일 또는 디렉토리의 전체 경로입니다.
            destination (Optional[str], unused): 이 매개변수는 다른 API와의 일관성을 위해 존재하지만,
                                                 삭제 작업에서는 사용되지 않습니다.

        Returns:
            Tuple[bool, Optional[str]]: (삭제 성공 여부, 백업 파일/디렉토리 경로)
                                       - 삭제 성공 시: (True, "백업된_경로.zip 또는 파일")
                                       - 삭제할 대상이 없거나 실패 시: (False, None)

        처리 과정:
        1. 소스 경로가 실제 존재하는지 확인합니다.
        2. 존재한다면, `_get_backup_path`를 이용해 백업 경로를 생성합니다.
        3. 소스가 디렉토리이면 `shutil.copytree`로, 파일이면 `shutil.copy2`로 백업 위치에 복사합니다.
        4. 백업 후, 소스가 디렉토리이면 `shutil.rmtree`로, 파일이면 `os.remove`로 삭제합니다.
        5. 성공 시 (True, 백업 경로)를 반환합니다.
        6. 소스 경로가 존재하지 않으면 (False, None)을 반환합니다.
        """
        try:
            if os.path.exists(source):
                backup_path = self._get_backup_path(source, "deleted")  # 백업 경로 생성

                # 백업 실행
                if os.path.isdir(source):
                    shutil.copytree(source, backup_path)  # 디렉토리 전체 복사
                else:
                    shutil.copy2(source, backup_path)  # 파일 복사 (메타데이터 포함)

                # 원본 삭제
                if os.path.isdir(source):
                    shutil.rmtree(source)  # 디렉토리와 그 내용 모두 삭제
                else:
                    os.remove(source)  # 파일 삭제

                return True, backup_path  # 성공 및 백업 경로 반환

            print(f"정보 (delete_item): 삭제할 대상 '{source}'가 존재하지 않습니다.")
            return False, None  # 삭제할 대상이 없음
        except Exception as e:
            print(f"오류 (delete_item): 삭제 중 ('{source}') 예외 발생: {e}")
            return False, None

    def __create_directory(self, source: str, destination: Optional[str] = None) -> Optional[str]:
        """
        'source' 경로에 새 디렉토리를 생성합니다. 이미 존재하더라도 오류를 발생시키지 않습니다 (exist_ok=True).
        성공 시 생성된 디렉토리의 경로를 반환하고, 실패 시 None을 반환합니다.
        이 메서드는 `execute_script`를 통해 "create_directory" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 생성할 새 디렉토리의 전체 경로입니다. 부모 디렉토리가 없으면 함께 생성됩니다.
            destination (Optional[str], unused): API 일관성을 위해 존재하나 사용되지 않습니다.

        Returns:
            Optional[str]: 디렉토리 생성 성공 시 해당 디렉토리의 경로 문자열을 반환합니다.
                           실패 시 None을 반환합니다.
        """
        try:
            os.makedirs(source, exist_ok=True)  # 디렉토리 생성, 이미 존재해도 오류 없음. 중간 경로도 생성.
            return source  # 성공 시 생성된 경로 반환
        except Exception as e:
            print(f"오류 (create_directory): 디렉토리 생성 중 ('{source}') 예외 발생: {e}")
            return None

    def __get_item_metadata(self, source: str, destination: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        'source' 경로에 있는 파일 또는 디렉토리의 메타데이터를 조회하여 딕셔너리 형태로 반환합니다.
        메타데이터에는 존재 여부, 이름, 전체 경로, 크기, 생성/수정/접근 시간, 디렉토리 여부, 확장자 등이 포함됩니다.
        실패하거나 경로가 존재하지 않으면 상세 정보를 포함한 딕셔너리(exists: False) 또는 None을 반환합니다.
        이 메서드는 `execute_script`를 통해 "get_metadata" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 메타데이터를 조회할 파일 또는 디렉토리의 전체 경로입니다.
            destination (Optional[str], unused): API 일관성을 위해 존재하나 사용되지 않습니다.

        Returns:
            Optional[Dict[str, Any]]: 조회 성공 시 메타데이터를 담은 딕셔너리를 반환합니다.
                                      키는 다음과 같습니다:
                                      - "exists" (bool): 경로 존재 여부.
                                      - "name" (str): 파일/디렉토리 이름.
                                      - "path" (str): 절대 경로.
                                      - "size" (int): 크기 (바이트 단위). 디렉토리의 경우 내부 모든 파일 크기의 합.
                                      - "created" (str): 생성 시간 (ISO 8601 형식).
                                      - "modified" (str): 마지막 수정 시간 (ISO 8601 형식).
                                      - "accessed" (str): 마지막 접근 시간 (ISO 8601 형식).
                                      - "is_directory" (bool): 디렉토리 여부.
                                      - "extension" (str): 파일 확장자 (소문자, 예: ".txt"). 디렉토리의 경우 빈 문자열.
                                      경로가 존재하지 않거나 오류 발생 시, {"exists": False, "path": source, "error": "에러메시지"} 형태의
                                      딕셔너리를 반환할 수 있습니다. 심각한 오류 시 None을 반환할 수도 있습니다.

        처리 과정:
        1. 소스 경로 존재 여부 확인. 없으면 {"exists": False, "path": source} 반환.
        2. `os.stat()`으로 파일 시스템 상태 정보 획득.
        3. 디렉토리 여부 확인 (`os.path.isdir()`).
        4. 수집된 정보를 바탕으로 메타데이터 딕셔너리 구성.
           - 디렉토리 크기는 `_get_dir_size` 헬퍼 메서드를 통해 재귀적으로 계산.
           - 시간 정보는 ISO 형식 문자열로 변환.
        """
        try:
            if not os.path.exists(source):
                # 경로가 존재하지 않는 경우, 명시적으로 존재하지 않음을 알리는 메타데이터 반환
                return {"exists": False, "path": source}

            stat_info = os.stat(source)  # 파일/디렉토리의 상태 정보
            is_dir = os.path.isdir(source)  # 디렉토리인지 여부

            metadata: Dict[str, Any] = {
                "exists": True,
                "name": os.path.basename(source),  # 경로에서 파일/디렉토리 이름만 추출
                "path": os.path.abspath(source),  # 정규화된 절대 경로
                "size": stat_info.st_size if not is_dir else self._get_dir_size(source),  # 파일 크기 또는 디렉토리 크기
                "created": datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),  # 생성 시간
                "modified": datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),  # 수정 시간
                "accessed": datetime.datetime.fromtimestamp(stat_info.st_atime).isoformat(),  # 접근 시간
                "is_directory": is_dir,
                "extension": os.path.splitext(source)[1].lower() if not is_dir else "",  # 파일 확장자 (소문자로)
            }
            return metadata
        except Exception as e:
            print(f"오류 (get_metadata): 메타데이터 조회 중 ('{source}') 예외 발생: {e}")
            # 오류 발생 시에도 'exists: False'와 오류 정보를 포함하여 반환
            return {"exists": False, "path": source, "error": str(e)}

    def __list_directory_contents(self, source: str, destination: Optional[str] = None) -> Optional[List[str]]:
        """
        'source' 디렉토리 내에 있는 직계 자식 항목(파일 및 하위 디렉토리)들의 전체 경로 목록을 반환합니다.
        재귀적으로 탐색하지 않습니다. (예: /a/b, /a/c 는 반환하지만 /a/b/d 는 반환하지 않음)
        실패하거나 'source'가 디렉토리가 아니면 None을 반환합니다.
        이 메서드는 `execute_script`를 통해 "list_directory" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 내용을 조회할 디렉토리의 전체 경로입니다.
            destination (Optional[str], unused): API 일관성을 위해 존재하나 사용되지 않습니다.

        Returns:
            Optional[List[str]]: 성공 시, 디렉토리 내 항목들의 절대 경로 문자열 리스트를 반환합니다.
                                 'source'가 디렉토리가 아니거나 오류 발생 시 None을 반환합니다.
        """
        try:
            if not os.path.isdir(source):
                print(f"오류 (list_directory): '{source}'는 디렉토리가 아닙니다.")
                return None  # 디렉토리가 아니면 작업 실패
            # os.listdir()은 상대 경로를 반환하므로, os.path.join으로 절대 경로를 만들어 반환
            return [os.path.abspath(os.path.join(source, item)) for item in os.listdir(source)]
        except Exception as e:
            print(f"오류 (list_directory): 디렉토리 내용 조회 중 ('{source}') 예외 발생: {e}")
            return None

    def __list_directory_contents_recursive(
        self, source: str, destination: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        'source' 디렉토리 내의 모든 하위 항목(파일 및 디렉토리) 목록을 재귀적으로 탐색하여 전체 경로 리스트로 반환합니다.
        실패하거나 'source'가 디렉토리가 아니면 None을 반환합니다.
        이 메서드는 `execute_script`를 통해 "list_directory_recursive" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 내용을 재귀적으로 조회할 최상위 디렉토리의 전체 경로입니다.
            destination (Optional[str], unused): API 일관성을 위해 존재하나 사용되지 않습니다.

        Returns:
            Optional[List[str]]: 성공 시, 지정된 디렉토리 및 모든 하위 디렉토리 내 항목들의
                                 절대 경로 문자열 리스트를 반환합니다.
                                 'source'가 디렉토리가 아니거나 오류 발생 시 None을 반환합니다.
        """
        all_items: List[str] = []
        try:
            if not os.path.isdir(source):
                print(f"오류 (list_directory_recursive): '{source}'는 디렉토리가 아닙니다.")
                return None  # 디렉토리가 아니면 작업 실패

            # os.walk는 (현재 디렉토리 경로, 하위 디렉토리 목록, 현재 디렉토리 내 파일 목록) 튜플을 생성
            for root, dirs, files in os.walk(source):
                for name in files:  # 현재 디렉토리의 파일들
                    all_items.append(os.path.abspath(os.path.join(root, name)))
                for name in dirs:  # 현재 디렉토리의 하위 디렉토리들
                    all_items.append(os.path.abspath(os.path.join(root, name)))
            return all_items
        except Exception as e:
            print(f"오류 (list_directory_recursive): 디렉토리 내용 재귀적 조회 중 ('{source}') 예외 발생: {e}")
            return None

    def __path_exists(self, source: str, destination: Optional[str] = None) -> bool:
        """
        'source'로 지정된 경로에 파일 또는 디렉토리가 실제로 존재하는지 확인합니다.
        이 메서드는 `execute_script`를 통해 "path_exists" 액션으로 호출되도록 의도되었습니다.

        Args:
            source (str): 존재 여부를 확인할 파일 또는 디렉토리의 전체 경로입니다.
            destination (Optional[str], unused): API 일관성을 위해 존재하나 사용되지 않습니다.

        Returns:
            bool: 경로가 존재하면 True, 그렇지 않으면 False를 반환합니다.
                  경로 문자열이 유효하지 않거나 접근 권한 문제 등으로 확인 불가 시 False를 반환할 수 있습니다.
        """
        try:
            return os.path.exists(source)
        except Exception as e:  # 경로 문자열이 너무 길거나 하는 등의 예외 처리
            print(f"오류 (path_exists): 경로 존재 확인 중 ('{source}') 예외 발생: {e}")
            return False

    def _get_dir_size(self, path: str) -> int:
        """
        지정된 디렉토리('path')의 총 크기를 바이트 단위로 계산하여 반환합니다.
        디렉토리 내의 모든 파일 크기를 합산합니다. 하위 디렉토리도 재귀적으로 포함합니다.
        심볼릭 링크는 크기 계산에서 제외될 수 있습니다 (os.path.getsize가 링크 대상의 크기를 반환할 수 있으므로 주의).
        이 메서드는 클래스 내부에서 주로 `__get_item_metadata`에 의해 사용됩니다.

        Args:
            path (str): 크기를 계산할 디렉토리의 전체 경로입니다.

        Returns:
            int: 디렉토리의 총 크기 (바이트). 오류 발생 시 0 또는 부분적인 크기를 반환할 수 있습니다.
        """
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(path):  # 디렉토리 트리 탐색
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    # 심볼릭 링크가 아니며 실제 파일인 경우에만 크기 계산에 포함
                    if os.path.exists(file_path) and not os.path.islink(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            print(f"내부 오류 (_get_dir_size): 디렉토리 크기 계산 중 ('{path}') 예외 발생: {e}")
            # 오류 발생 시, 지금까지 계산된 크기 또는 0을 반환할 수 있음
        return total_size

    def _resolve_value(self, value_or_symbol: Optional[Any], symbol_table: Dict[str, Any]) -> Optional[Any]:
        """
        주어진 값이 심볼 참조(예: "$my_var")인 경우, 심볼 테이블에서 해당 심볼의 실제 값을 찾아 반환합니다.
        값이 심볼이 아니거나 None이면, 주어진 값 그대로를 반환합니다.
        이 메서드는 `execute_script` 내부에서 각 명령어의 'source'와 'destination' 값을 처리할 때 사용됩니다.

        Args:
            value_or_symbol (Optional[Any]): 해석할 값 또는 심볼 문자열입니다.
                                             문자열이 아니거나, 문자열이지만 `self.symbol_prefix`로 시작하지 않으면
                                             심볼로 간주하지 않습니다.
            symbol_table (Dict[str, Any]): 현재까지 실행된 명령어들의 `result`로 저장된 심볼과 그 값들을
                                           매핑하는 딕셔너리입니다.

        Returns:
            Optional[Any]: 심볼인 경우 심볼 테이블에서 찾아낸 실제 값.
                           심볼이 아니거나 None인 경우 입력값 그대로.

        Raises:
            ValueError: 심볼 형태의 문자열이 주어졌으나, 해당 심볼이 심볼 테이블에 존재하지 않을 경우 발생합니다.
        """
        if value_or_symbol is None:
            return None  # 입력이 None이면 None 반환

        # 입력값이 문자열이고, 정의된 심볼 접두사로 시작하는 경우에만 심볼로 간주
        if isinstance(value_or_symbol, str) and value_or_symbol.startswith(self.symbol_prefix):
            symbol_name = value_or_symbol[len(self.symbol_prefix) :]  # 접두사를 제외한 심볼 이름 추출
            if symbol_name in symbol_table:
                return symbol_table[symbol_name]  # 심볼 테이블에서 값 조회 및 반환
            else:
                # 참조하려는 심볼이 테이블에 없을 경우 오류 발생
                raise ValueError(
                    f"심볼 '{symbol_name}'을(를) 찾을 수 없습니다. 사용 가능한 심볼: {list(symbol_table.keys())}"
                )

        return value_or_symbol  # 심볼이 아니면 입력값 그대로 반환

    def execute_script(self, instructions: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """
        명령어(instruction) 리스트로 구성된 스크립트를 순차적으로 실행합니다.
        각 명령어는 파일 시스템 작업을 나타내며, 한 명령어의 결과는 다음 명령어의 입력으로 사용될 수 있습니다 (파이프라이닝).
        스크립트 실행 중 하나의 명령어라도 실패하면, 이전에 성공한 변경 작업들을 가능한 범위 내에서 롤백하려고 시도합니다.

        Args:
            instructions (List[Dict[str, Any]]): 실행할 명령어들의 리스트입니다.
                각 명령어(딕셔너리)는 다음 키들을 가질 수 있습니다:
                - "action" (str, 필수): 수행할 작업의 종류 (예: "create_directory", "move_file").
                                       `self._actions` 딕셔너리에 정의된 키 중 하나여야 합니다.
                - "source" (Any, 선택): 작업의 주 입력 소스 (예: 파일 경로, 디렉토리 경로).
                                        심볼 참조 (예: "$prev_result")가 가능합니다.
                - "destination" (Any, 선택): 작업의 대상 또는 부가 정보 (예: 이동될 경로, 새 이름).
                                             심볼 참조가 가능합니다. 액션에 따라 사용되지 않을 수 있습니다.
                - "result" (str, 선택): 이 명령어의 실행 결과를 저장할 심볼의 이름입니다.
                                        여기에 저장된 값은 후속 명령어에서 `self.symbol_prefix`를 사용하여 참조할 수 있습니다.

        Returns:
            Tuple[bool, Dict[str, Any]]:
            - 첫 번째 요소 (bool): 스크립트 전체의 실행 성공 여부입니다. 모든 명령어가 성공하면 True, 하나라도 실패하면 False.
            - 두 번째 요소 (Dict[str, Any]): 스크립트 실행 중 생성된 모든 심볼과 그 값들을 담은 심볼 테이블입니다.
                                           스크립트 실패 시에도, 실패 지점까지 생성된 심볼들이 포함될 수 있습니다.
        """
        symbol_table: Dict[str, Any] = {}  # 현재 스크립트 실행 세션의 심볼들을 저장
        executed_actions_log: List[Dict[str, Any]] = []  # 롤백을 위해 성공한 변경 작업들을 기록
        overall_success = True  # 스크립트 전체의 성공 여부를 추적

        for i, instruction in enumerate(instructions):  # 각 명령어를 순회
            action_name: Optional[str] = instruction.get("action")
            raw_source: Optional[Any] = instruction.get("source")  # 심볼 해석 전의 source 값
            raw_destination: Optional[Any] = instruction.get("destination")  # 심볼 해석 전의 destination 값
            result_symbol: Optional[str] = instruction.get("result")  # 결과를 저장할 심볼 이름

            # 1. 명령어 유효성 검사 (action 필드)
            if not action_name or action_name not in self._actions:
                print(
                    f"오류 (명령어 {i+1}): 유효하지 않거나 정의되지 않은 액션 '{action_name}'입니다. 명령어: {instruction}"
                )
                overall_success = False
                break  # 스크립트 실행 중단

            action_func = self._actions[action_name]  # 실행할 내부 메서드 가져오기

            resolved_source: Optional[Any] = None  # 심볼 해석 후의 source 값
            resolved_destination: Optional[Any] = None  # 심볼 해석 후의 destination 값

            try:
                # 2. source 및 destination 값 심볼 해석
                resolved_source = self._resolve_value(raw_source, symbol_table)

                if action_name == "rename_item":
                    # 'rename_item' 액션의 destination은 심볼 해석 대상이 아닌 '새 이름' 문자열임
                    if not isinstance(raw_destination, str):
                        raise ValueError(
                            f"'rename_item' 액션의 'destination'은 새 이름을 나타내는 문자열이어야 합니다. 전달된 값: {raw_destination} (타입: {type(raw_destination)})"
                        )
                    resolved_destination = raw_destination  # 심볼 해석 없이 그대로 사용
                else:
                    resolved_destination = self._resolve_value(raw_destination, symbol_table)

                # 3. 필수 인자 타입 및 경로 유효성 검사 (주로 경로 문자열을 기대하는 액션들)
                #    액션별로 필요한 인자의 타입이 다를 수 있으므로, 각 액션의 특성에 맞게 검사해야 합니다.
                #    여기서는 경로 기반 액션들에 대해 source/destination이 문자열인지 주로 확인합니다.
                path_based_actions = [
                    "move_file",
                    "rename_item",
                    "delete_item",
                    "create_directory",
                    "get_metadata",
                    "list_directory",
                    "list_directory_recursive",
                    "path_exists",
                ]
                if action_name in path_based_actions:
                    # 'source'가 경로 문자열이어야 하는 경우
                    if resolved_source is not None and not isinstance(resolved_source, str):
                        print(
                            f"오류 (명령어 {i+1}): 액션 '{action_name}'의 'source'는 경로 문자열이어야 합니다 (해석된 값: '{resolved_source}', 타입: {type(resolved_source)}). 명령어: {instruction}"
                        )
                        overall_success = False
                        break
                    if resolved_source is None and action_name not in []:  # source가 None이면 안되는 액션들
                        print(
                            f"오류 (명령어 {i+1}): 액션 '{action_name}'에는 유효한 'source' 경로가 필요합니다. 명령어: {instruction}"
                        )
                        overall_success = False
                        break

                    # 'destination'이 경로 문자열이어야 하는 경우 (예: move_file)
                    if action_name in ["move_file"]:
                        if resolved_destination is not None and not isinstance(resolved_destination, str):
                            print(
                                f"오류 (명령어 {i+1}): 액션 '{action_name}'의 'destination'은 경로 문자열이어야 합니다 (해석된 값: '{resolved_destination}', 타입: {type(resolved_destination)}). 명령어: {instruction}"
                            )
                            overall_success = False
                            break
                        if resolved_destination is None:  # move_file은 destination이 필수
                            print(
                                f"오류 (명령어 {i+1}): 액션 '{action_name}'에는 유효한 'destination' 경로가 필요합니다. 명령어: {instruction}"
                            )
                            overall_success = False
                            break

                # 4. 실제 액션 함수 호출
                action_result: Any = None
                log_entry: Optional[Dict[str, Any]] = None  # 롤백을 위한 로그 항목 (변경 작업인 경우에만 기록)

                # 각 액션 함수는 정의된 매개변수에 맞게 호출되어야 합니다.
                if action_name in ["delete_item"]:
                    # __delete_item(self, source: str, destination: Optional[str] = None) -> Tuple[bool, Optional[str]]
                    success_flag, backup_path = action_func(resolved_source)
                    action_result = success_flag
                    if success_flag and backup_path:  # 삭제 성공 및 백업 경로 존재 시 롤백 로그 기록
                        log_entry = {
                            "action": "delete_item",
                            "source_for_reverse": resolved_source,
                            "backup_path_for_reverse": backup_path,
                        }

                elif action_name == "rename_item":
                    # __rename_item(self, source: str, new_name: str) -> Optional[str]
                    action_result = action_func(
                        resolved_source, resolved_destination
                    )  # resolved_destination이 new_name
                    if action_result:  # 성공 시 (새 경로 반환) 롤백 로그 기록
                        log_entry = {
                            "action": "rename_item",
                            "source_for_reverse": action_result,  # 롤백 시 source는 현재의 새 경로
                            "destination_for_reverse": os.path.basename(str(resolved_source)),
                        }  # 롤백 시 destination은 이전 이름

                elif action_name == "move_file":
                    # __move_file(self, source: str, destination: str) -> Optional[str]
                    action_result = action_func(resolved_source, resolved_destination)
                    if action_result:  # 성공 시 (대상 경로 반환) 롤백 로그 기록
                        log_entry = {
                            "action": "move_file",
                            "source_for_reverse": action_result,  # 롤백 시 source는 현재의 대상 경로
                            "destination_for_reverse": resolved_source,
                        }  # 롤백 시 destination은 원래 소스 경로

                elif action_name == "create_directory":
                    # __create_directory(self, source: str, destination: Optional[str] = None) -> Optional[str]
                    action_result = action_func(resolved_source)
                    if action_result:  # 성공 시 (생성된 경로 반환) 롤백 로그 기록
                        log_entry = {
                            "action": "create_directory",
                            "source_for_reverse": action_result,
                        }  # 롤백 시 삭제할 경로

                else:  # get_metadata, list_directory, path_exists 등 (주로 롤백 불필요)
                    # destination 인자를 사용하는 다른 함수들을 위해 일반화된 호출 (필요시 추가)
                    if (
                        resolved_destination is not None and action_name in []
                    ):  # 예시: "copy_file" 등이 destination을 사용한다면
                        action_result = action_func(resolved_source, resolved_destination)
                    else:  # 대부분 source만 사용
                        action_result = action_func(resolved_source)

                # 5. 액션 결과 확인 및 심볼 저장
                #    - path_exists 액션은 False도 유효한 결과이므로 예외 처리.
                #    - 다른 액션들은 결과가 None이거나 (bool 타입일 경우) False이면 실패로 간주.
                if action_result is None or (
                    isinstance(action_result, bool) and not action_result and action_name != "path_exists"
                ):
                    print(
                        f"오류 (명령어 {i+1}): 액션 '{action_name}'이 실패했습니다. 소스: '{resolved_source}', 대상: '{resolved_destination}'. 명령어: {instruction}"
                    )
                    overall_success = False
                    break  # 스크립트 실행 중단

                if result_symbol:  # 'result' 키에 심볼 이름이 지정된 경우
                    symbol_table[result_symbol] = action_result  # 심볼 테이블에 결과 저장

                if log_entry:  # 파일 시스템에 변경을 가하는 작업이었다면 롤백 로그에 추가
                    executed_actions_log.append(log_entry)

            except ValueError as ve:  # 심볼 해석 오류, 잘못된 값 전달 등
                print(f"값 오류 (명령어 {i+1}): {ve}. 명령어: {instruction}")
                overall_success = False
                break
            except TypeError as te:  # 함수 호출 시 잘못된 타입의 인자가 전달될 때
                print(
                    f"타입 오류 (명령어 {i+1}): {te}. 액션: '{action_name}', 소스: '{resolved_source}', 대상: '{resolved_destination}'. 명령어: {instruction}"
                )
                overall_success = False
                break
            except Exception as e:  # 그 외 예상치 못한 모든 예외
                print(
                    f"예상치 못한 오류 (명령어 {i+1}): 액션 '{action_name}' 실행 중 예외 발생: {e}. 명령어: {instruction}"
                )
                overall_success = False
                break

        # 6. 스크립트 실행 완료 후 처리
        if not overall_success:  # 하나 이상의 명령어가 실패했다면
            print("하나 이상의 명령어가 실패하여, 가능한 작업에 대해 롤백을 시도합니다...")
            self._rollback_actions(executed_actions_log)  # 기록된 변경 작업들을 롤백
            return False, symbol_table  # 실패 및 현재까지의 심볼 테이블 반환

        return True, symbol_table  # 모든 명령어가 성공한 경우, 성공 및 최종 심볼 테이블 반환

    def _rollback_actions(self, executed_actions: List[Dict[str, Any]]) -> None:
        """
        실행된 작업들(`executed_actions_log`에 기록된)을 역순으로 되돌립니다.
        이 메서드는 `execute_script`에서 스크립트 실행이 실패했을 때 호출됩니다.

        Args:
            executed_actions (List[Dict[str, Any]]): 롤백할 작업들의 로그 리스트입니다.
                                                     각 로그는 `execute_script`에서 정의된 `log_entry` 형식입니다.
        """
        # 로그에 기록된 작업들을 역순으로 (가장 최근 작업부터) 처리하여 롤백 시도
        for action_log in reversed(executed_actions):
            try:
                print(f"롤백 시도 중: {action_log.get('action')} (소스: {action_log.get('source_for_reverse')})")
                if not self.reverse_action(action_log):
                    # 롤백 실패 시 경고를 출력하지만, 다음 롤백 작업은 계속 시도합니다.
                    print(f"경고: 다음 작업의 롤백에 실패했습니다: {action_log}")
            except Exception as e:
                print(f"롤백 중 예외 발생 (작업 로그: {action_log}): {e}")

    def reverse_action(self, action_log: Dict[str, Any]) -> bool:
        """
        `action_log`에 기록된 특정 파일 시스템 변경 작업을 실행 취소하려고 시도합니다.
        각 액션 타입에 맞는 역방향 작업을 수행합니다.

        Args:
            action_log (Dict[str, Any]): 실행 취소할 작업에 대한 세부 정보가 담긴 딕셔너리입니다.
                                         `execute_script`의 `log_entry`와 형식이 일치해야 합니다.
                                         필요한 키 예시: "action", "source_for_reverse", "destination_for_reverse", "backup_path_for_reverse"

        Returns:
            bool: 작업 실행 취소(롤백) 성공 여부를 반환합니다. 성공 시 True, 실패 시 False.
        """
        action_type = action_log.get("action")

        try:
            if action_type == "move_file":
                # 원본 로그: {"action": "move_file", "source_for_reverse": 현재위치(원래destination), "destination_for_reverse": 원래source}
                # 롤백 실행: __move_file(현재위치, 원래source) -> 즉, 파일을 원래 위치로 다시 옮김
                source = str(action_log.get("source_for_reverse"))
                destination = str(action_log.get("destination_for_reverse"))
                return self.__move_file(source, destination) is not None  # 성공 시 경로 반환, 실패 시 None

            elif action_type == "rename_item":
                # 원본 로그: {"action": "rename_item", "source_for_reverse": 새경로(현재이름), "destination_for_reverse": 이전이름}
                # 롤백 실행: __rename_item(새경로, 이전이름) -> 즉, 파일 이름을 원래 이름으로 되돌림
                source = str(action_log.get("source_for_reverse"))
                new_name_for_rollback = str(action_log.get("destination_for_reverse"))
                return self.__rename_item(source, new_name_for_rollback) is not None

            elif action_type == "delete_item":
                # 원본 로그: {"action": "delete_item", "source_for_reverse": 삭제된경로, "backup_path_for_reverse": 백업된경로}
                # 롤백 실행: 백업된 경로에서 원래 삭제된 경로로 파일/디렉토리 복원
                backup_path = action_log.get("backup_path_for_reverse")
                original_source = action_log.get("source_for_reverse")

                if backup_path and original_source and os.path.exists(backup_path):
                    # 복원 대상 위치에 이미 다른 파일/디렉토리가 있는 경우 충돌 방지 처리 (선택적)
                    if os.path.exists(original_source):
                        temp_name = (
                            f"{original_source}.rollback_conflict_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}"
                        )
                        os.rename(original_source, temp_name)  # 기존 항목 임시 이름으로 변경
                        print(
                            f"정보 (롤백): 복원 대상 위치 '{original_source}'에 항목이 존재하여 '{temp_name}'으로 변경 후 복원 시도합니다."
                        )

                    if os.path.isdir(backup_path):  # 백업된 것이 디렉토리면 copytree 사용
                        shutil.copytree(backup_path, original_source)
                    else:  # 파일이면 copy2 사용
                        shutil.copy2(backup_path, original_source)

                    # 복원 후 백업 파일은 유지하거나 삭제할 수 있습니다 (정책에 따라 결정).
                    # 예: shutil.rmtree(backup_path) or os.remove(backup_path)
                    print(f"정보 (롤백): '{backup_path}' 에서 '{original_source}'로 복원 성공.")
                    return True
                else:
                    print(
                        f"오류 (롤백): delete_item 롤백 실패. 백업 경로 '{backup_path}' 또는 원본 소스 '{original_source}'가 유효하지 않거나 존재하지 않습니다."
                    )
                    return False

            elif action_type == "create_directory":
                # 원본 로그: {"action": "create_directory", "source_for_reverse": 생성된디렉토리경로}
                # 롤백 실행: 생성된 디렉토리 삭제.
                # 주의: 이 디렉토리 내에 다른 파일이 롤백 과정에서 생성되었을 수 있으므로,
                #       안전하게 비어있는 경우에만 삭제하거나, shutil.rmtree 사용 시 주의.
                created_path = action_log.get("source_for_reverse")
                if created_path and os.path.isdir(created_path):
                    try:
                        # 디렉토리가 비어있지 않아도 삭제하려면 shutil.rmtree 사용
                        # 여기서는 os.rmdir을 사용하여 빈 디렉토리만 삭제 시도 (더 안전)
                        # 또는 __delete_item을 호출할 수도 있으나, delete_item은 다시 백업을 생성하므로 순환 발생 가능성.
                        # 여기서는 직접 삭제 로직을 구현하거나, 백업 없는 삭제 함수를 별도 호출.
                        if not os.listdir(created_path):  # 디렉토리가 비어있는 경우
                            os.rmdir(created_path)
                        else:  # 비어있지 않은 경우 (shutil.rmtree로 강제 삭제 또는 실패 처리)
                            shutil.rmtree(created_path)  # 내용물과 함께 삭제 (주의해서 사용)
                            # print(f"경고 (롤백): 생성되었던 디렉토리 '{created_path}'가 비어있지 않지만 강제 삭제 시도.")
                        print(f"정보 (롤백): 생성되었던 디렉토리 '{created_path}' 삭제 성공.")
                        return True
                    except OSError as e_rmdir:  # 디렉토리가 비어있지 않으면 OSError 발생 가능
                        print(f"오류 (롤백): 생성되었던 디렉토리 '{created_path}' 삭제 실패: {e_rmdir}")
                        return False
                elif created_path and not os.path.exists(created_path):
                    print(f"정보 (롤백): 생성되었던 디렉토리 '{created_path}'가 이미 존재하지 않아 롤백 불필요.")
                    return True  # 이미 없음 = 롤백 성공 간주
                else:
                    print(
                        f"오류 (롤백): create_directory 롤백 실패. 유효한 생성 경로 '{created_path}'를 찾을 수 없습니다."
                    )
                    return False

            else:  # 등록되지 않은 액션 타입의 롤백 요청
                print(f"경고 (롤백): 알 수 없거나 롤백이 지원되지 않는 액션 타입입니다: '{action_type}'")
                return False

        except Exception as e_reverse:
            print(f"오류 (롤백): 액션 '{action_type}' (로그: {action_log}) 롤백 중 예외 발생: {e_reverse}")
            return False

    def get_api_list(self) -> List[str]:
        """
        현재 `FileSystemManager` 인스턴스에서 사용 가능한 모든 API 액션(action) 이름들의 리스트(List)를 반환합니다.
        `get_api_names`와 유사하지만, 순서가 있는 리스트 형태로 반환합니다 (순서는 내부 딕셔너리 정의에 따름).

        Returns:
            List[str]: 지원되는 모든 API 액션 이름들의 리스트입니다.
                       (예: ['move_file', 'rename_item', 'create_directory', ...])
        """
        return list(self._actions.keys())
