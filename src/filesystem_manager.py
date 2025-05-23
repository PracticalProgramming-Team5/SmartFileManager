import datetime
import os
import shutil
from typing import Any, Callable, Dict, List, Set, Optional


class FileSystemManager:
    """
    실제 파일 시스템 작업을 실행하고 안전하게 수행되도록 보장합니다.

    사용 예시:
    ```python
    # 인스턴스 생성
    fs_manager = FileSystemManager()

    # 개별 API 사용은 불가능하며 계획 실행만 가능
    # 여러 작업 동시 실행 및 롤백 자동화
    actions = [
        {"action": "create_directory", "source": "/path/to/new_dir"},
        {"action": "move", "source": "/path/from/file.txt", "destination": "/path/to/new_dir/file.txt"}
    ]
    success = fs_manager.execute_plan(actions)  # 모두 성공하면 True, 아니면 자동 롤백
    ```
    """

    def __init__(self):
        """필요한 상태를 초기화합니다."""
        self.backup_dir = os.path.join(os.path.expanduser("~"), ".smartfilemanager", "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

        # API 액션을 메소드에 매핑하는 딕셔너리
        self._actions: Dict[str, Callable[..., Any]] = {
            "move": self.__move_file,
            "rename": self.__rename_item,
            "delete": self.__delete_item,
            "create_directory": self.__create_directory,
            "get_metadata": self.__get_item_metadata,
            "list_directory": self.__list_directory_contents,
            "list_directory_recursive": self.__list_directory_contents_recursive,
            "path_exists": self.__path_exists,
        }

    def __move_file(self, source: str, destination: str) -> bool:
        """
        파일을 이동하고 성공 여부를 반환합니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "move", "source": "/home/user/file.txt", "destination": "/home/user/documents/file.txt"}]
        fs_manager.execute_plan(plan)
        ```

        Args:
            source: 이동할 파일 경로
            destination: 대상 경로

        Returns:
            작업 성공 여부
        """
        try:
            dest_dir = os.path.dirname(destination)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)

            if os.path.exists(destination):
                backup_name = f"{os.path.basename(destination)}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                backup_path = os.path.join(self.backup_dir, backup_name)
                shutil.copy2(destination, backup_path)

            shutil.move(source, destination)
            return True

        except Exception as e:
            print(f"파일 이동 중 오류 발생: {e}")
            return False

    def __rename_item(self, source: str, destination: str) -> bool:
        """
        파일 또는 디렉토리의 이름을 변경합니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "rename", "source": "/home/user/oldname.txt", "destination": "newname.txt"}]
        fs_manager.execute_plan(plan)
        ```

        Args:
            source: 이름을 변경할 항목 경로
            destination: 새 이름 (파일/폴더명만, 경로 아님)

        Returns:
            작업 성공 여부
        """
        try:
            dir_path = os.path.dirname(source)
            new_path = os.path.join(dir_path, destination)

            if os.path.exists(new_path):
                backup_name = f"{destination}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                backup_path = os.path.join(self.backup_dir, backup_name)
                shutil.copy2(new_path, backup_path)

            os.rename(source, new_path)
            return True

        except Exception as e:
            print(f"이름 변경 중 오류 발생: {e}")
            return False

    def __delete_item(self, source: str, destination: Optional[str] = None) -> bool:
        """
        파일 또는 디렉토리를 삭제합니다. 삭제 전에 백업을 생성합니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "delete", "source": "/home/user/file_to_delete.txt"}]
        fs_manager.execute_plan(plan)
        ```

        Args:
            source: 삭제할 항목 경로
            destination: 사용하지 않음(API 일관성을 위해 포함)

        Returns:
            작업 성공 여부
        """
        try:
            if os.path.exists(source):
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                backup_name = f"{os.path.basename(source)}.deleted.{timestamp}"
                backup_path = os.path.join(self.backup_dir, backup_name)

                if os.path.isdir(source):
                    shutil.copytree(source, backup_path)
                else:
                    shutil.copy2(source, backup_path)

                if os.path.isdir(source):
                    shutil.rmtree(source)
                else:
                    os.remove(source)

                return True
            return False

        except Exception as e:
            print(f"삭제 중 오류 발생: {e}")
            return False

    def __create_directory(self, source: str, destination: Optional[str] = None) -> bool:
        """
        새 디렉토리를 생성합니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "create_directory", "source": "/home/user/new_directory"}]
        fs_manager.execute_plan(plan)
        ```

        Args:
            source: 생성할 디렉토리 경로
            destination: 사용하지 않음(API 일관성을 위해 포함)

        Returns:
            작업 성공 여부
        """
        try:
            os.makedirs(source, exist_ok=True)
            return True
        except Exception as e:
            print(f"디렉토리 생성 중 오류 발생: {e}")
            return False

    def __get_item_metadata(self, source: str, destination: Optional[str] = None) -> Dict[str, Any]:
        """
        메타데이터(크기, 유형, 날짜 등)를 가져옵니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "get_metadata", "source": "/home/user/file.txt", "result_var": "metadata"}]
        result = fs_manager.execute_plan(plan)
        if result:
            metadata = plan[0].get("result")
            print(f"파일 크기: {metadata['size']} 바이트")

        # 반환된 메타데이터 형식 예시:
        # {
        #   "exists": True,
        #   "name": "file.txt",
        #   "path": "/home/user/file.txt",
        #   "size": 1024,
        #   "created": "2023-01-01T12:00:00.123456",
        #   "modified": "2023-01-02T15:30:45.654321",
        #   "accessed": "2023-01-03T10:15:20.987654",
        #   "is_directory": False,
        #   "extension": ".txt"
        # }
        ```

        Args:
            source: 메타데이터를 가져올 항목 경로
            destination: 사용하지 않음(API 일관성을 위해 포함)

        Returns:
            항목 메타데이터를 담은 사전
        """
        try:
            # 경로가 존재하지 않으면 exists=False로 간단히 반환
            if not os.path.exists(source):
                return {"exists": False}

            # 파일/디렉토리 상태 정보 획득
            stat_info: os.stat_result = os.stat(source)
            is_dir = os.path.isdir(source)

            # 메타데이터 사전 구성
            # - exists: 항목 존재 여부 (항상 True, 존재하지 않으면 위에서 이미 반환)
            # - name: 경로에서 파일/디렉토리 이름만 추출
            # - path: 전체 경로 (원본 그대로)
            # - size: 파일 크기 또는 디렉토리의 경우 재귀적으로 내부 파일 크기 합산
            # - created/modified/accessed: 생성/수정/접근 시간을 ISO 형식 문자열로 변환
            # - is_directory: 디렉토리 여부
            # - extension: 파일인 경우 확장자 (소문자로 정규화), 디렉토리는 빈 문자열
            metadata: Dict[str, Any] = {
                "exists": True,
                "name": os.path.basename(source),
                "path": source,
                "size": stat_info.st_size if not is_dir else self._get_dir_size(source),
                "created": datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                "modified": datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                "accessed": datetime.datetime.fromtimestamp(stat_info.st_atime).isoformat(),
                "is_directory": is_dir,
                "extension": os.path.splitext(source)[1].lower() if not is_dir else "",
            }

            return metadata

        except Exception as e:
            # 오류 발생 시 존재하지 않는 것으로 처리하고 오류 메시지 포함
            print(f"메타데이터 가져오는 중 오류 발생: {e}")
            return {"exists": False, "error": str(e)}

    def __list_directory_contents(self, source: str, destination: Optional[str] = None) -> list[str]:
        """
        파일 및 하위 디렉토리 목록을 가져옵니다.

        주의: 이 메서드는 첫 번째 수준의 항목만 반환합니다 (재귀적이지 않음).
        재귀적으로 모든 파일을 나열하려면 list_directory_recursive 액션을 사용하세요.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "list_directory", "source": "/home/user/documents", "result_var": "contents"}]
        result = fs_manager.execute_plan(plan)
        if result:
            contents = plan[0].get("result")
            for item in contents:
                print(f"발견된 항목: {item}")

                # 각 항목의 메타데이터도 획득하려면
                metadata_plan = [{"action": "get_metadata", "source": item, "result_var": "item_metadata"}]
                fs_manager.execute_plan(metadata_plan)
                item_metadata = metadata_plan[0].get("result")

                if item_metadata["is_directory"]:
                    print(f"디렉토리: {item}")
                else:
                    print(f"파일: {item}, 크기: {item_metadata['size']} 바이트")
        ```

        Args:
            source: 내용을 가져올 디렉토리 경로
            destination: 사용하지 않음(API 일관성을 위해 포함)

        Returns:
            파일 및 하위 디렉토리 경로 목록 (전체 경로 포함)
        """
        try:
            # 입력이 디렉토리가 아니면 빈 목록 반환
            if not os.path.isdir(source):
                return []

            return [os.path.join(source, item) for item in os.listdir(source)]

        except Exception as e:
            print(f"디렉토리 내용 나열 중 오류 발생: {e}")
            return []

    def __list_directory_contents_recursive(self, source: str, destination: Optional[str] = None) -> list[str]:
        """
        디렉토리의 모든 파일과 하위 디렉토리를 재귀적으로 가져옵니다.

        이 함수는 지정된 디렉토리와 그 아래의 모든 하위 디렉토리에 있는
        모든 파일 및 디렉토리의 전체 경로 목록을 반환합니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "list_directory_recursive", "source": "/home/user/documents", "result_var": "all_files"}]
        result = fs_manager.execute_plan(plan)
        if result:
            all_files = plan[0].get("result")
            print(f"총 {len(all_files)}개 항목 발견:")

            # 발견된 파일들을 순회
            for file_path in all_files:
                # 파일 경로 출력
                print(file_path)
        ```

        Args:
            source: 재귀적으로 내용을 가져올 디렉토리 경로
            destination: 사용하지 않음(API 일관성을 위해 포함)

        Returns:
            모든 하위 파일 및 디렉토리의 전체 경로 목록
        """
        all_items: list[str] = []

        try:
            # 입력이 디렉토리가 아니면 빈 목록 반환
            if not os.path.isdir(source):
                return []

            # 현재 디렉토리의 모든 항목을 가져옴
            for item in os.listdir(source):
                item_path = os.path.join(source, item)
                # 현재 항목을 목록에 추가
                all_items.append(item_path)

                # 디렉토리인 경우 재귀적으로 내부 항목도 가져옴
                if os.path.isdir(item_path):
                    all_items.extend(self.__list_directory_contents_recursive(item_path))

            return all_items

        except Exception as e:
            print(f"디렉토리 내용 재귀적 나열 중 오류 발생: {e}")
            return all_items  # 오류가 발생해도 이미 수집된 항목은 반환

    def __path_exists(self, source: str, destination: Optional[str] = None) -> bool:
        """
        경로의 존재 여부를 확인합니다.

        사용 예시:
        ```python
        # 직접 호출하지 말고 execute_plan을 사용
        plan = [{"action": "path_exists", "source": "/home/user/file.txt", "result_var": "exists"}]
        result = fs_manager.execute_plan(plan)
        if result:
            exists = plan[0].get("result")
            if exists:
                print("파일이 존재합니다")
            else:
                print("파일이 존재하지 않습니다")
        ```

        Args:
            source: 확인할 경로
            destination: 사용하지 않음(API 일관성을 위해 포함)

        Returns:
            경로 존재 여부
        """
        return os.path.exists(source)

    def get_api_names(self) -> Set[str]:
        """
        사용 가능한 모든 API 메서드 이름 목록을 반환합니다.

        사용 예시:
        ```python
        api_names = fs_manager.get_api_names()
        print(f"사용 가능한 API: {api_names}")
        # 출력: 사용 가능한 API: {'move', 'rename', 'delete', 'create_directory', 'get_metadata', ...}
        ```

        Returns:
            API 메서드 이름 집합
        """
        return set(self._actions.keys())

    def get_api_list(self) -> List[str]:
        """
        사용 가능한 모든 API 메서드 이름 목록을 리스트로 반환합니다.

        사용 예시:
        ```python
        api_list = fs_manager.get_api_list()
        print("사용 가능한 작업:")
        for api in api_list:
            print(f"- {api}")
        ```

        Returns:
            API 메서드 이름 리스트
        """
        return list(self._actions.keys())

    def execute_plan(self, actions: list[Dict[str, Any]]) -> bool:
        """
        API 액션 시퀀스를 실행합니다.

        사용 예시:
        ```python
        # 복잡한 작업을 계획으로 정의
        plan = [
            {"action": "create_directory", "source": "/home/user/project"},
            {"action": "create_directory", "source": "/home/user/project/docs"},
            {"action": "create_directory", "source": "/home/user/project/src"},
            {"action": "move", "source": "/home/user/file1.txt", "destination": "/home/user/project/docs/readme.txt"},
            {"action": "move", "source": "/home/user/code.py", "destination": "/home/user/project/src/main.py"},
        ]

        # 계획 실행 (하나라도 실패하면 모든 작업 롤백)
        success = fs_manager.execute_plan(plan)
        if success:
            print("모든 작업이 성공적으로 완료되었습니다.")
        else:
            print("일부 작업이 실패하여 모든 변경사항이 롤백되었습니다.")

        # 정보 조회 액션은 결과를 해당 액션에 저장합니다
        info_plan = [
            {"action": "path_exists", "source": "/home/user/file.txt", "result_var": "exists"},
            {"action": "get_metadata", "source": "/home/user/documents", "result_var": "doc_meta"},
            {"action": "list_directory", "source": "/home/user/downloads", "result_var": "files"}
        ]
        fs_manager.execute_plan(info_plan)

        # 결과 액세스
        exists = info_plan[0].get("result")
        metadata = info_plan[1].get("result")
        file_list = info_plan[2].get("result")
        ```

        Args:
            actions: 실행할 액션 시퀀스 (각 액션은 'action', 'source', 'destination' 키를 포함)

        Returns:
            모든 작업의 성공 여부
        """
        success = True
        executed_actions: List[Dict[str, Any]] = []

        try:
            for action in actions:
                action_type = action.get("action")
                source = action.get("source", "")
                destination = action.get("destination", None)

                if not action_type or not source:
                    print(f"잘못된 액션 형식: {action}")
                    success = False
                    break

                try:
                    if action_type not in self._actions:
                        raise KeyError(f"API 메서드 '{action_type}'이(가) 존재하지 않습니다")

                    result = self._actions[action_type](source, destination)

                    # 결과 저장 (get_metadata, list_directory, path_exists 등에 사용)
                    if "result_var" in action:
                        action["result"] = result

                    # Boolean이 아닌 결과도 성공으로 처리하되 저장
                    if isinstance(result, bool) and not result:
                        success = False
                        self._rollback_actions(executed_actions)
                        break

                    # 표준화된 형식으로 작업 기록 (롤백용)
                    if action_type in ["move", "rename", "delete", "create_directory"]:
                        standardized_action: Dict[str, Any] = {
                            "action": action_type,
                            "source": source,
                            "destination": destination,
                        }

                        # 백업 경로 정보 추가 (나중에 복원을 위해)
                        if action_type == "delete":
                            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                            backup_name = f"{os.path.basename(source)}.deleted.{timestamp}"
                            backup_path = os.path.join(self.backup_dir, backup_name)
                            standardized_action["backup_path"] = backup_path

                        executed_actions.append(standardized_action)

                except KeyError as e:
                    print(f"계획 실행 중 오류 발생: {e}")
                    success = False
                    self._rollback_actions(executed_actions)
                    break

            return success

        except Exception as e:
            print(f"계획 실행 중 오류 발생: {e}")
            self._rollback_actions(executed_actions)
            return False

    def reverse_action(self, action_log: Dict[str, Any]) -> bool:
        """
        기록된 특정 작업을 실행 취소하려고 시도합니다.

        Args:
            action_log: 실행 취소할 작업에 대한 세부 정보 (표준화된 형식)

        Returns:
            실행 취소 성공 여부
        """
        try:
            action_type = action_log.get("action")
            source = action_log.get("source", "")
            destination = action_log.get("destination")

            if not action_type or not source:
                print(f"잘못된 액션 로그 형식: {action_log}")
                return False

            if action_type == "move":
                # 이동 작업의 실행 취소는 역방향 이동
                if destination is not None and source is not None:
                    return self.__move_file(destination, source)
                else:
                    print(
                        f"reverse_action: source 또는 destination이 None입니다: source={source}, destination={destination}"
                    )
                    return False

            elif action_type == "rename":
                # 이름 변경의 실행 취소는 원래 이름으로 되돌리기
                if destination is not None:
                    return self.__rename_item(source, destination)
                else:
                    print(f"reverse_action: destination이 None입니다: source={source}, destination={destination}")
                    return False

            elif action_type == "delete":
                # 삭제의 실행 취소는 백업에서 복원
                backup_path = action_log.get("backup_path")

                if backup_path and os.path.exists(backup_path):
                    if os.path.isdir(backup_path):
                        shutil.copytree(backup_path, source)
                    else:
                        shutil.copy2(backup_path, source)
                    return True
                return False

            elif action_type == "create_directory":
                # 디렉토리 생성 취소는 삭제
                return self.__delete_item(source)

            return False

        except Exception as e:
            print(f"작업 실행 취소 중 오류 발생: {e}")
            return False

    def _get_dir_size(self, path: str) -> int:
        """
        디렉토리의 총 크기를 계산합니다. (내부 헬퍼 메소드)

        Args:
            path: 디렉토리 경로

        Returns:
            디렉토리 총 크기(바이트)
        """
        total_size = 0
        for dirpath, _, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                total_size += os.path.getsize(file_path)
        return total_size

    def _rollback_actions(self, executed_actions: List[Dict[str, Any]]) -> None:
        """
        이미 실행된 작업들을 역순으로 되돌립니다. (내부 롤백 프로세스)

        Args:
            executed_actions: 실행된 작업 목록
        """
        for action in reversed(executed_actions):
            try:
                self.reverse_action(action)
            except Exception as e:
                print(f"롤백 중 오류 발생: {e}")
