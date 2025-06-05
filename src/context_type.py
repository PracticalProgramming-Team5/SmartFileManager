from typing import List, Tuple, Any
from pydantic import BaseModel

# json 파싱 형식 정의
class ActionMove(BaseModel):
    source: str
    tags: Tuple[str, ...]
    destination: Tuple[str, ...]
    explanation: Tuple[str, ...]
    def __repr__(self):
        return self.model_dump_json(indent=2)

class ActionCommand(BaseModel):
    action: str
    source: str
    destination: str
    result: str
    def __repr__(self):
        return self.model_dump_json()

class ActionCommandList(BaseModel):
    plan: List[ActionCommand]
    explanation: str
    def __repr__(self):
        return self.model_dump_json(indent=2)


EXAMPLE_PAYLOAD = ActionCommandList(
    plan=[
        ActionCommand(
            action="사용자 제공 API 1",
            source="source 인자",
            destination="destination 인자",
            result="API 실행 결과를 저장할 심볼"
        ),
        ActionCommand(
            action="사용자 제공 API 2",
            source="source 인자",
            destination="destination 인자",
            result="API 실행 결과를 저장할 심볼"
        )
    ],
    explanation="위 스크립트의 동작과정을 한 문장으로 설명"
)

EXAMPLE_PAYLOAD2 = ActionMove(
    source="some/source/path",
    tags=("tag1", "tag2", "tag3", "etc."),
    destination=("dest/path1", "dest/path2", "dest/path3"),
    explanation=(
        "dest/path1을 추천하는 이유",
        "dest/path2을 추천하는 이유",
        "dest/path3을 추천하는 이유",
    )
)

EXAMPLE_PAYLOAD_ = ActionCommandList(
    plan=[
        ActionCommand(
            action="list_directory",
            source="some/abs/source/picutres",
            destination="",
            result="pictures_files"
        ),
        ActionCommand(
            action="mask_expr",
            source="pictures_files",
            destination="['*.png', '*.jpg', '*.jpeg', '*.webp']",
            result="masked_files"
        ),
        ActionCommand(
            action="delete",
            source="masked_files",
            destination="",
            result=""
        )
    ],
    explanation="pictures 디렉토리의 사진 파일들을 전부 삭제합니다."
)

EXAMPLE_PAYLOAD_2 = ActionCommandList(
    plan=[
    ],
    explanation="해당 명령을 수행할 수 있는 API 조합이 없습니다."
)