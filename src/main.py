import os
import sys

# 현재 스크립트의 디렉토리를 시스템 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

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
