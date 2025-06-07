import sqlite3
from typing import List, Dict, Set
import os

# 절대 경로인지 검사
def _is_relative_path(path: str):
    return not os.path.isabs(path)

# 파일 경로 정규화
def _normalize(p: str) -> str:
    return os.path.normpath(p).replace("\\", "/")

class FileTagDB:
    def __init__(self, db_path: str = 'file_tags.db'):
        self.conn = sqlite3.connect(db_path)
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_tags (
                    file_path TEXT PRIMARY KEY,
                    tags TEXT
                )
                """
            )

    def add_file(self, file_path: str, tags: List[str]) -> bool:
        """
        데이터베이스에서 파일에 태그를 추가하거나 업데이트합니다.
        
        Args:
            file_path(str): 파일의 절대 경로
            tags(List): 파일 태그, 최대 10개
        
        Returns:
            bool(bool): 작업 성공 여부
        """
        file_path = _normalize(file_path)
        if _is_relative_path(file_path): return False
        if len(tags) > 10: return False
        tags_str = ','.join(tags)
        try:
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO file_tags (file_path, tags) VALUES (?, ?)",
                    (file_path, tags_str)
                )
        except Exception as e:
            return False
        return True

    def rename_file(self, old_path: str, new_path: str) -> bool:
        """
        데이터베이스에서 파일 경로를 수정합니다.

        Args:
            old_path(str): 기존 파일의 절대 경로
            new_path(str): 새 파일의 절대 경로

        Returns:
            bool(bool): 작업 성공 여부
        """
        old_path = _normalize(old_path)
        new_path = _normalize(new_path)
        if _is_relative_path(old_path): return False
        if _is_relative_path(new_path): return False
        try:
            with self.conn:
                self.conn.execute(
                    "UPDATE file_tags SET file_path = ? WHERE file_path = ?",
                    (new_path, old_path)
                )
        except Exception as e:
            return False
        return True

    def delete_file(self, file_path: str) -> bool:
        """
        데이터베이스에서 파일을 삭제합니다.

        Args:
            file_path(str): 파일의 절대 경로
        
        Returns:
            bool(bool): 작업 성공 여부
        """
        file_path = _normalize(file_path)
        if _is_relative_path(file_path): return False
        try:
            with self.conn:
                cur = self.conn.execute(
                    "DELETE FROM file_tags WHERE file_path = ?",
                    (file_path,)
                )
                return cur.rowcount > 0
        except Exception as e:
            return False

    def get_tags(self, file_path: str) -> List[str]:
        """
        단일 파일의 태그 리스트를 반환합니다.
        
        Args:
            file_path(str): 파일의 절대 경로

        Returns:
            list(List[str]): 태그 리스트
        """
        file_path = _normalize(file_path)
        if _is_relative_path(file_path): return []
        try:
            cur = self.conn.execute(
                "SELECT tags FROM file_tags WHERE file_path = ?",
                (file_path,)
            )
            row = cur.fetchone()
            return row[0].split(',') if row and row[0] else []
        except Exception as e:
            return []

    def get_tags_by_directory(self, dir_path: str) -> set[str]:
        """
        지정한 디렉토리의 태그를 반환합니다. 하위 디렉토리는 반영되지 않습니다.
        
        Args:
            dir_path(str): 디렉토리의 절대 경로
        
        Returns:
            tags(set[str]): 디렉토리 하위 파일들의 태그들
        """
        dir_path = _normalize(dir_path)
        if _is_relative_path(dir_path):
            return set()

        prefix = dir_path.rstrip("/") + "/"
        tags_set: Set[str] = set()
        # prefix 바로 아래(1단계)만: prefix% 이면서, prefix 길이+1 이후에 / 없을 것
        sql = """
        SELECT tags
        FROM file_tags
        WHERE file_path LIKE ?
        AND instr(
                substr(file_path, length(?) + 1),
                ?
            ) = 0
        """
        params = (prefix + '%', prefix, "/")
        try:
            cur = self.conn.execute(sql, params)
            for (tags_str,) in cur.fetchall():
                if tags_str:
                    tags_set.update(tags_str.split(','))
            return tags_set
        except Exception as e:
            return set()
    def get_all(self) -> Dict[str, List[str]]:
        """
        DB에 저장된 모든 파일 경로와 태그 리스트를 반환합니다.

        Returns:
            dict: { file_path: [tag1, tag2, ...], ... }
        """
        try:
            cur = self.conn.execute("SELECT file_path, tags FROM file_tags")
            all_data: Dict[str, List[str]] = {}
            for file_path, tags_str in cur.fetchall():
                all_data[file_path] = tags_str.split(',') if tags_str else []
            return all_data
        except Exception:
            return {}
        
    def close(self):
        """DB 연결 해제"""
        self.conn.close()