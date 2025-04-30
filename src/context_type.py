from typing import List, Tuple
from pydantic import BaseModel

# json 파싱 형식 정의
class ActionMove(BaseModel):
    source: str
    destination: Tuple[str, ...]
    explanation: Tuple[str, ...]
    def __repr__(self):
        return self.model_dump_json(indent=2)

class ActionCommand(BaseModel):
    action: str
    source: str
    destination: str
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
            source="some/source/path1",
            destination="some/dest/path1"
        ),
        ActionCommand(
            action="사용자 제공 API 2",
            source="some/source/path2",
            destination="some/dest/path2"
        )
    ],
    explanation="위 스크립트의 동작과정을 한 문장으로 설명"
)

EXAMPLE_PAYLOAD2 = ActionMove(
    source="some/source/path",
    destination=("dest/path1", "dest/path2", "dest/path3"),
    explanation=(
        "dest/path1을 추천하는 이유",
        "dest/path2을 추천하는 이유",
        "dest/path3을 추천하는 이유",
    )
)