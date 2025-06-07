import os
from typing import List
from PyQt5.QtCore import QObject, pyqtSlot, QThread
from event_hub import EventHub, AppEvent, Worker

from settings_manager import SettingsManager
from filesystem_manager import FileSystemManager
from llm_client import LLMClient, LLMErrorCode
from history_manager import HistoryManager
from context_builder import ContextBuilder
from response_parser import ResponseParser
from directory_monitor import DirectoryMonitor
from ui_manager import UIManager
from script_excuter import ScriptExecuter
from tagdb import FileTagDB
"""
이벤트 목록
    1. 메인 윈도우 오픈 -> UI
    2. 백그라운드 시작
    3. 백그라운드 종료
    4. 창닫기 (백그라운드 상태 포함한) -> UI

    5. 인스턴트 윈도우 오픈 -> UI
    6. 명령어 입력
    7. 명령어 응답 전송
    8. 명령어 실행 요청
    9. 명령 수행 완료 -> UI, backend

    10. 관심 디렉토리 내 파일 생성 알림 (추천 경로 포함)  -> UI, backend
    11. move 요청

    12. 핫키 입력 -> UI

class AppEvent:
    target: str
    event: str
    data: object
"""


class FileManagerCore(QObject):
    def __init__(self, event_hub):
        super().__init__()
        self.event_hub = event_hub
        self.event_hub.event.connect(self.__process_event)
        self.runnable = False

        # self.settings_manager = SettingsManager()

        # self.history_manager = HistoryManager()
        # self.llm_client = LLMClient()
        self.context_builder = ContextBuilder(self.fs)
        # self.script_exe = ScriptExecuter()
        self.tag_db = FileTagDB()
        # self.res_parse = ResponseParser()
        # self.dir_monitor = DirectoryMonitor()
    def __process_event(self, event: EventHub):
        if event.name == "CoreRun": # 백그라운드 동작
            self.runnable = True
        elif event.name == "CoreStop": # 백그라운드 정지
            self.runnable = False
            self.__clear()
        
        if not self.runnable:
            return

        if event.name == "CoreReqComm": # 유저가 커맨드 제출
            system_msg, prompt = self.context_builder.format_command_prompt(event.data)
            llm_client = LLMClient()
            thread = QThread()
            worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreResComm")
            worker.moveToThread(thread)
            worker.destroyed.connect(thread.deleteLater)
            
        elif event.name == "CoreResComm": # LLM 명령어 응답 도착
            msg, success = event.data
            if not success == LLMErrorCode.SUCCESS:
                print("예외 처리 해야 함")
                return
            script, success = self.res_parse.parse_action_command(msg)
            if success:
                self.event_hub.event.emit(AppEvent("UiResComm", {'res': True, 'script':script}))
                print("성공 반환")
            else:
                self.event_hub.event.emit(AppEvent("UiResComm", {'res': False, 'script':None}))
                print("실패 반환")
        
        elif event.name == "CoreReqOper": # Operation 요청
            script_exe = ScriptExecuter()
            thread = QThread()
            worker = Worker(lambda: script_exe.run_script(event.data), self.event_hub, "CoreResOper")
            worker.moveToThread(thread)
            worker.destroyed.connect(thread.deleteLater)
        elif event.name == "CoreResOper": # Operation 반환
            e = event.data
            if e:
                print("실패", e)
                return
            print("성공")
        elif event.name == "CoreResDir": # LLM 추천 경로 응답 도착
            self.event_hub.event.emit(AppEvent("UiResComm", {'res': True, 'script':script}))
        elif event.name == "CoreReqMov": # 유저가 이동 요청
            src = event.data['src']
            dest = event.data['dest']
            
            script_exe = ScriptExecuter()
            thread = QThread()
            worker = Worker(lambda: script_exe.move(src, dest), self.event_hub, "CoreResMov")
            worker.moveToThread(thread)
            worker.destroyed.connect(thread.deleteLater)
        elif event.name == "CoreResMov": # 명령 결과
            print("이따 구현")
        ####
        if event.name == "CoreFileAdd": # 파일 생성
            system_msg, prompt = self.context_builder.format_move_prompt(event.data)

            llm_client = LLMClient()
            thread = QThread()
            worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreFileAddRes")
            worker.moveToThread(thread)
            worker.destroyed.connect(thread.deleteLater)
            # 유저가 검사한 항목이라면 검사하지 않음. -> 일단 그냥 항상 띄움.
            # 1. 적절한 위치를 요청(with getting tag)
            # 2. 태깅
            # 3. UI
        elif event.name == "CoreFileAddRes": # 파일 생성에 대한 LLM 응답
            self.tag_db.add_file(file_path=event.data.source, tags=event.data.tags)
            #self.event_hub.emit()
            print("LLM 응답 -> UI")
        elif event.name == "CoreFileMov": # 파일 이동
            self.tag_db.rename_file(old_path=event.data['old_data'], new_path=event.data['new_path']) # 수정
        elif event.name == "CoreFileDel": # 파일 삭제
            self.tag_db.delete_file(file_path=event.data.source)
    
    def __clear(self):
        pass
# class FileManagerCore:
#     def __init__(self, settings_path, event_hub):
#         self.settings = SettingsManager()
#         self.fs = FileSystemManager()
#         self.history = HistoryManager()
#         self.llm = LLMClient()
#         self.context_builder = ContextBuilder(self.fs)
#         self.response_interpreter = ResponseParser()
#         self.runnable = False
        
#         self.event_hub = event_hub
#         self.event_hub.event.connect(self.__process_event)
    
#     def __process_event(self, e):
#         pass

#     def run(self):
#         print("run")

#     def stop(self):
#         print("앱 종료 및 리소스 정리")

    # def handle_new_file(self, file_path: str):
    #     file_ctx = self.context_builder.get_file_context(file_path, detail_level="partial")
    #     root_dir = os.path.dirname(file_path)
    #     dir_structure = self.context_builder.get_directory_structure(root_dir)
    #     prompt = self.context_builder.format_move_prompt(file_ctx, dir_structure)

    #     response, err = self.llm.query(self.context_builder.system_prompt_move, prompt)
    #     if not response:
    #         self.ui.display_results("LLM 응답 오류 발생")
    #         return

    #     suggestions = self.response_interpreter.parse_action_move(response)
    #     self.ui.display_path_suggestions(file_path, suggestions)

    # def handle_natural_language_command(self, command: str):
    #     root_dir = os.getcwd()
    #     dir_structure = self.context_builder.get_directory_structure(root_dir)
    #     prompt = self.context_builder.format_command_prompt(command, dir_structure)

    #     response, err = self.llm.query(self.context_builder.system_prompt_script, prompt)
    #     if not response:
    #         self.ui.display_results("LLM 명령 처리 실패")
    #         return

    #     plan = self.response_interpreter.parse_action_command(response)
    #     if not plan:
    #         self.ui.display_results("LLM 응답 해석 실패")
    #         return

    #     # 명령어 필터링 로직 적용
    #     allowed = self.settings_manager.get_allowed_commands()
    #     blocked = self.settings_manager.get_blocked_commands()
    #     interested = self.settings_manager.get_interested_commands()

    #     filtered_plan = []
    #     for cmd in plan['plan']:
    #         action = cmd.get('action')
    #         if action in blocked:
    #             self.ui.display_results(f"⛔ 차단된 명령어: {action} (수행하지 않음)")
    #             continue
    #         if action in interested:
    #             print(f"⭐ 관심 명령어 감지됨: {action}")  # 또는 UI에서 강조
    #         if allowed and action not in allowed:
    #             self.ui.display_results(f"⚠️ 허용되지 않은 명령어: {action} (수행하지 않음)")
    #             continue
    #         filtered_plan.append(cmd)

    #     if not filtered_plan:
    #         self.ui.display_results("실행 가능한 명령어가 없습니다.")
    #         return

    #     self.ui.display_action_plan({'plan': filtered_plan, 'explanation': plan['explanation']})

    #     confirmed = self.ui.prompt_for_confirmation("작업을 실행할까요?", ["예", "아니오"])
    #     if confirmed != "예":
    #         return

    #     if self.fs.execute_plan(filtered_plan):
    #         for action in filtered_plan:
    #             self.history.log_action(action)
    #         self.ui.display_results("작업 완료")
    #     else:
    #         self.ui.display_results("작업 실패")