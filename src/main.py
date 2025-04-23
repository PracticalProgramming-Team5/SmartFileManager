import os
import sys
from file_manager_core import FileManagerCore


def main():
    """애플리케이션의 메인 엔트리 포인트"""
    # 설정 파일 경로 설정
    settings_path = os.path.join(
        os.path.expanduser("~"), ".smartfilemanager", "settings.json"
    )

    # 애플리케이션 코어 초기화
    app = FileManagerCore(settings_path)

    # 애플리케이션 시작
    app.start()


if __name__ == "__main__":
    main()
