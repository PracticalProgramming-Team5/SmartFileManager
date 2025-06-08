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
from script_excuter import ScriptExecuter
from tagdb import FileTagDB

class WrapDirectoryMonitor(QObject):
    def __init__(self, event_hub):
        super().__init__()
        self.event_hub = event_hub
        def parse_monitor(src, dst, code):
            name, data = "", {}
            if code == 0:
                name, data = "CoreFileAdd", {"src":src}
            elif code == 1:
                name, data = "CoreFiledel", {"src":src}
            else:
                name, data = "CoreFileMov", {"src":src, "dst":dst}
            # print(name, data, "-------")
            self.event_hub.event.emit(AppEvent(name, data))
            # print(name, data)
        self.dir_monitor = DirectoryMonitor(parse_monitor)
    def start(self):
        for dirs in SettingsManager.get('monitoring_dirs'):
            self.dir_monitor.add_directory(dirs)
        self.dir_monitor.start()
    def stop(self):
        self.dir_monitor.stop()


class FileManagerCore(QObject):
    def __init__(self, event_hub: EventHub):
        super().__init__()
        self.event_hub = event_hub
        self.event_hub.event.connect(self.__process_event)
        self.runnable = True

        # self.history_manager = HistoryManager()
        # self.context_builder = ContextBuilder()
        self.tag_db = FileTagDB()
        
        self.dir_monitor = WrapDirectoryMonitor(event_hub)

    def __process_event(self, event: AppEvent):
        print("back:", event.name)
        if event.name == "CoreRun": # 백그라운드 동작
            self.runnable = True
            self.dir_monitor.start()
            self.event_hub.event.emit(AppEvent("UiResCoreState", self.runnable))

        elif event.name == "CoreStop": # 백그라운드 정지
            self.runnable = False
            self.dir_monitor.stop()
            self.__clear()
        
        if not self.runnable:
            return

        elif event.name == "CoreReqCommand": # 유저가 커맨드 제출
            self.context_builder = ContextBuilder()
            system_msg, prompt = self.context_builder.format_command_prompt(event.data)
            print(system_msg, prompt)
            llm_client = LLMClient()
            self.thread = QThread()
            self.worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreResCommand")
            # self.worker = Worker(lambda: None, self.event_hub, "CoreResCommand")
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.started.connect(self.worker.run)
            self.thread.start()

        elif event.name == "CoreResCommand": # LLM 명령어 응답 도착
            msg, success = event.data
            
            success = LLMErrorCode.SUCCESS
            
            
            script, success = ResponseParser.parse_action_command(msg)
            if not success:
                script = {'plan': []}
            # print(script)
            self.event_hub.event.emit(AppEvent("UiResCommand", script))
        
        elif event.name == "CoreReqOper": # Operation 요청
            self.script_exe = ScriptExecuter()
            self.thread = QThread()
            print(event.data)
            # self.worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreResCommand")
            self.worker = Worker(lambda: self.script_exe.run_script(event.data), self.event_hub, "CoreResOper")
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
        elif event.name == "CoreResOper": # Operation 반환
            e = event.data if event.data != "None" else None # 수정 필요
            print(event.data)
            self.event_hub.event.emit(AppEvent("UiResOper", e))
            
            if not e is None:
                print("실패", e)
                return
            print("성공")
        elif event.name == "CoreResDir": # LLM 추천 경로 응답 도착
            self.event_hub.event.emit(AppEvent("UiResRecommend", {'res': True, 'script':script}))
        elif event.name == "CoreReqMov": # 유저가 이동 요청
            src, dest = event.data
            
            self.script_exe = ScriptExecuter()

            self.thread = QThread()
            # self.worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreResCommand")
            self.worker = Worker(lambda: self.script_exe.move(src, dest), self.event_hub, "CoreResMov")
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
        elif event.name == "CoreResMov": # 명령 결과
            e = event.data
            self.event_hub.event.emit(AppEvent("UiResFile", e))
            if e:
                print("실패", e)
                return
            print("성공")
        ####
        elif event.name == "CoreFileAdd": # 파일 생성
            self.context_builder = ContextBuilder()
            system_msg, prompt = self.context_builder.format_move_prompt(file_path=event.data['src'], max_depth=1)
            # print(system_msg, prompt)
            self.llm_client = LLMClient()
            # print("check1", event.name)
            self.thread = QThread()
            # print("check2", event.name)
            # self.worker = Worker(lambda: None, self.event_hub, "CoreFileAddRes")
            self.worker = Worker(lambda: self.llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreFileAddRes")
            # print("check3", event.name)
            self.worker.moveToThread(self.thread)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.started.connect(self.worker.run)
            self.thread.start()
            # print("check4", event.name)
            # 유저가 검사한 항목이라면 검사하지 않음. -> 일단 그냥 항상 띄움.
            # 1. 적절한 위치를 요청(with getting tag)
            # 2. 태깅
            # 3. UI
        elif event.name == "CoreFileAddRes": # 파일 생성에 대한 LLM 응답
            # print(event.data)
            res, err = event.data
            # res = """json\n{\n  "source": "/Users/ssw/Downloads/watchdog_tmp copy.py",\n  "tags": [\n    "python",\n    "script",\n    "temporary",\n    "development",\n    "code",\n    "programming",\n    "automation",\n    "file_monitoring",\n    "backup",\n    "project"\n  ],\n  "destination": [\n    "/Users/ssw/Documents/school/25_practical_programming/team5/src",\n    "/Users/ssw/Downloads/tmp_sources",\n    "/Users/ssw/Downloads/test"\n  ],\n  "explanation": [\n    "/Users/ssw/Documents/school/25_practical_programming/team5/src을 추천하는 이유: 프로젝트 관련 소스 코드가 저장되는 디렉토리로 보이며, Python 스크립트가 여기에 적합합니다.",\n    "/Users/ssw/Downloads/tmp_sources을 추천하는 이유: 임시 소스 파일을 저장하기에 적합한 디렉토리로 보입니다.",\n    "/Users/ssw/Downloads/test을 추천하는 이유: 테스트 및 임시 파일을 저장하기에 적합한 디렉토리로 보입니다."\n  ]\n}\n"""
            res, err = ResponseParser.parse_action_move(res)
            # print(res)
            print("파일 생성")
            self.tag_db.add_file(file_path=res['source'], tags=['tags'])
            self.event_hub.event.emit(AppEvent("UiAddFile", res))
        elif event.name == "CoreFileMov": # 파일 이동
            print("파일 이동")
            self.tag_db.rename_file(old_path=event.data['src'], new_path=event.data['dst']) # 수정
        elif event.name == "CoreFileDel": # 파일 삭제
            print("파일 삭제")
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