import sqlite3
from typing import List, Dict, Set
import os

def _validate_absolute_path(path: str):
    return not os.path.isabs(path)

def _normalize(p: str) -> str:
    return os.path.normpath(p)

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
        if _validate_absolute_path(file_path): return False
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
        if _validate_absolute_path(old_path): return False
        if _validate_absolute_path(new_path): return False
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
        if _validate_absolute_path(file_path): return False
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
        if _validate_absolute_path(file_path): return []
        try:
            cur = self.conn.execute(
                "SELECT tags FROM file_tags WHERE file_path = ?",
                (file_path,)
            )
            row = cur.fetchone()
            return row[0].split(',') if row and row[0] else []
        except Exception as e:
            return []

    def get_tags_by_directory(self, dir_path: str) -> Dict[str, List[str]]:
        """
        지정한 디렉토리의 태그를 반환합니다. 하위 디렉토리는 반영되지 않습니다.
        
        Args:
            dir_path(str): 디렉토리의 절대 경로
        
        Returns:
            dict(Dict[str, List]): 디렉토리 하위 파일들의 태그들
        """
        dir_path = _normalize(dir_path)
        if _validate_absolute_path(dir_path):
            return set()

        prefix = dir_path.rstrip(os.sep) + os.sep
        tags_set: Set[str] = set()
        # prefix 바로 아래(1단계)만: prefix% 이면서, prefix 길이+1 이후에 os.sep 없을 것
        sql = """
        SELECT tags
        FROM file_tags
        WHERE file_path LIKE ?
        AND instr(
                substr(file_path, length(?) + 1),
                ?
            ) = 0
        """
        params = (prefix + '%', prefix, os.sep)

        cur = self.conn.execute(sql, params)
        for (tags_str,) in cur.fetchall():
            if tags_str:
                tags_set.update(tags_str.split(','))
        return tags_set
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
                # tags 컬럼이 빈 문자열일 수도 있으므로 안전하게 분리
                all_data[file_path] = tags_str.split(',') if tags_str else []
            return all_data
        except Exception:
            return {}
        
    def close(self):
        """DB 연결 해제"""
        self.conn.close()

# if __name__ == '__main__':
#     db = FileTagDB(':memory:')
#     try:
#         # 1) 파일 추가 및 조회
#         test_file = os.path.abspath('/tmp/test.txt')
#         tags = ['alpha', 'beta', 'gamma']
#         db.add_file(test_file, tags)
#         assert db.get_tags(test_file) == tags
#         print('add_file/get_tags: PASS')

#         # 2) 태그 업데이트
#         new_tags = ['one', 'two']
#         db.add_file(test_file, new_tags)
#         assert db.get_tags(test_file) == new_tags
#         print('update tags: PASS')

#         # 3) 파일명 변경
#         renamed = os.path.abspath('/tmp/renamed.txt')
#         db.rename_file(test_file, renamed)
#         assert db.get_tags(renamed) == new_tags
#         assert db.get_tags(test_file) == []
#         print('rename_file: PASS')

#         # 4) 디렉토리 조회 (중복 제거된 태그 집합 반환)
#         other_file = os.path.abspath('/tmp/subdir/other.log')
#         other_tags = ['x', 'y']
#         db.add_file(other_file, other_tags)
#         tag_set = db.get_tags_by_directory(os.path.abspath('/tmp'))
#         expected_set = set(new_tags)
#         print(tag_set)
#         print(db.get_tags_by_directory(os.path.abspath('/tmp/subdir')))
#         assert tag_set == expected_set
#         print('get_tags_by_directory: PASS')

#         # 5) 삭제 기능
#         assert db.delete_file(renamed) is True
#         assert db.get_tags(renamed) == []
#         assert db.delete_file(renamed) is False
#         print('delete_file: PASS')

#     finally:
#         print("nice")
#         db.close()