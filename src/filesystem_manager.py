import datetime
import os
import shutil
from typing import Any, Dict, List


class FileSystemManager:
    """
    실제 파일 시스템 작업을 실행하고 안전하게 수행되도록 보장합니다.
    """

    def __init__(self):
        """필요한 상태를 초기화합니다."""
        self.backup_dir = os.path.join(
            os.path.expanduser("~"), ".smartfilemanager", "backups"
        )
        os.makedirs(self.backup_dir, exist_ok=True)

    def move_file(self, source: str, destination: str) -> bool:
        """
        파일을 이동하고 성공 여부를 반환합니다.

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

    def rename_item(self, path: str, new_name: str) -> bool:
        """
        파일 또는 디렉토리의 이름을 변경합니다.

        Args:
            path: 이름을 변경할 항목 경로
            new_name: 새 이름

        Returns:
            작업 성공 여부
        """
        try:
            dir_path = os.path.dirname(path)
            new_path = os.path.join(dir_path, new_name)

            if os.path.exists(new_path):
                backup_name = (
                    f"{new_name}.bak.{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                )
                backup_path = os.path.join(self.backup_dir, backup_name)
                shutil.copy2(new_path, backup_path)

            os.rename(path, new_path)
            return True

        except Exception as e:
            print(f"이름 변경 중 오류 발생: {e}")
            return False

    def delete_item(self, path: str) -> bool:
        """
        파일 또는 디렉토리를 삭제합니다.

        Args:
            path: 삭제할 항목 경로

        Returns:
            작업 성공 여부
        """
        try:
            if os.path.exists(path):
                timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                backup_name = f"{os.path.basename(path)}.deleted.{timestamp}"
                backup_path = os.path.join(self.backup_dir, backup_name)

                if os.path.isdir(path):
                    shutil.copytree(path, backup_path)
                else:
                    shutil.copy2(path, backup_path)

                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)

                return True
            return False

        except Exception as e:
            print(f"삭제 중 오류 발생: {e}")
            return False

    def create_directory(self, path: str) -> bool:
        """
        새 디렉토리를 생성합니다.

        Args:
            path: 생성할 디렉토리 경로

        Returns:
            작업 성공 여부
        """
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            print(f"디렉토리 생성 중 오류 발생: {e}")
            return False

    def get_item_metadata(self, path: str) -> Dict[str, Any]:
        """
        메타데이터(크기, 유형, 날짜 등)를 가져옵니다.

        Args:
            path: 메타데이터를 가져올 항목 경로

        Returns:
            항목 메타데이터를 담은 사전
        """
        try:
            if not os.path.exists(path):
                return {"exists": False}

            stat_info = os.stat(path)
            is_dir = os.path.isdir(path)

            metadata: Dict[str, Any] = {
                "exists": True,
                "name": os.path.basename(path),
                "path": path,
                "size": stat_info.st_size if not is_dir else self._get_dir_size(path),
                "created": datetime.datetime.fromtimestamp(
                    stat_info.st_ctime
                ).isoformat(),
                "modified": datetime.datetime.fromtimestamp(
                    stat_info.st_mtime
                ).isoformat(),
                "accessed": datetime.datetime.fromtimestamp(
                    stat_info.st_atime
                ).isoformat(),
                "is_directory": is_dir,
                "extension": os.path.splitext(path)[1].lower() if not is_dir else "",
            }

            return metadata

        except Exception as e:
            print(f"메타데이터 가져오는 중 오류 발생: {e}")
            return {"exists": False, "error": str(e)}

    def list_directory_contents(self, path: str) -> list[str]:
        """
        파일 및 하위 디렉토리 목록을 가져옵니다.

        Args:
            path: 내용을 가져올 디렉토리 경로

        Returns:
            파일 및 하위 디렉토리 경로 목록
        """
        try:
            if not os.path.isdir(path):
                return []

            return [os.path.join(path, item) for item in os.listdir(path)]

        except Exception as e:
            print(f"디렉토리 내용 나열 중 오류 발생: {e}")
            return []

    def path_exists(self, path: str) -> bool:
        """
        경로의 존재 여부를 확인합니다.

        Args:
            path: 확인할 경로

        Returns:
            경로 존재 여부
        """
        return os.path.exists(path)

    def execute_plan(self, actions: list[Dict[str, Any]]) -> bool:
        """
        ResponseInterpreter가 제공한 작업 시퀀스를 실행합니다.

        Args:
            actions: 실행할 작업 시퀀스

        Returns:
            모든 작업의 성공 여부
        """
        success = True
        executed_actions: List[Dict[str, Any]] = []

        try:
            for action in actions:
                action_type = action.get("action")

                if action_type == "move":
                    result = self.move_file(
                        action.get("source", ""), action.get("destination", "")
                    )
                elif action_type == "rename":
                    result = self.rename_item(
                        action.get("path", ""), action.get("new_name", "")
                    )
                elif action_type == "delete":
                    result = self.delete_item(action.get("path", ""))
                elif action_type == "create_directory":
                    result = self.create_directory(action.get("path", ""))
                else:
                    print(f"알 수 없는 작업 유형: {action_type}")
                    result = False

                if result:
                    executed_actions.append(action)
                else:
                    success = False
                    # 실패 시 실행한 작업들 되돌리기
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
            action_log: 실행 취소할 작업에 대한 세부 정보

        Returns:
            실행 취소 성공 여부
        """
        try:
            action_type = action_log.get("action")

            if action_type == "move":
                # 이동 작업의 실행 취소는 역방향 이동
                return self.move_file(
                    action_log.get("destination", ""), action_log.get("source", "")
                )

            elif action_type == "rename":
                # 이름 변경의 실행 취소는 원래 이름으로 되돌리기
                # dir_path = os.path.dirname(action_log.get("new_path", ""))
                original_name = action_log.get("original_name", "")
                new_path = action_log.get("new_path", "")
                return self.rename_item(new_path, original_name)

            elif action_type == "delete":
                # 삭제의 실행 취소는 백업에서 복원
                backup_path = action_log.get("backup_path", "")
                original_path = action_log.get("path", "")

                if os.path.exists(backup_path):
                    if os.path.isdir(backup_path):
                        shutil.copytree(backup_path, original_path)
                    else:
                        shutil.copy2(backup_path, original_path)
                    return True
                return False

            elif action_type == "create_directory":
                # 디렉토리 생성 취소는 삭제
                return self.delete_item(action_log.get("path", ""))

            return False

        except Exception as e:
            print(f"작업 실행 취소 중 오류 발생: {e}")
            return False

    def _get_dir_size(self, path: str) -> int:
        """
        디렉토리의 총 크기를 계산합니다.

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
        이미 실행된 작업들을 역순으로 되돌립니다.

        Args:
            executed_actions: 실행된 작업 목록
        """
        for action in reversed(executed_actions):
            try:
                self.reverse_action(action)
            except Exception as e:
                print(f"롤백 중 오류 발생: {e}")
