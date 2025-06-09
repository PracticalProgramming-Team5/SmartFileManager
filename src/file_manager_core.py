from PyQt5.QtCore import QObject, QThreadPool
from event_hub import EventHub, AppEvent, Worker

from settings_manager import SettingsManager
from llm_client import LLMClient, LLMErrorCode
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
        self.runnable = False
        self.tag_db = FileTagDB()
        
        self.dir_monitor = WrapDirectoryMonitor(event_hub)
        self.thread_pool = QThreadPool()

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
            self.event_hub.event.emit(AppEvent("UiResCoreState", self.runnable))
        
        if not self.runnable:
            return

        elif event.name == "CoreReqCommand": # 유저가 커맨드 제출
            self.context_builder = ContextBuilder()
            system_msg, prompt = self.context_builder.format_command_prompt(event.data)
            print(system_msg, prompt)
            llm_client = LLMClient()
            worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreResCommand")
            self.thread_pool.start(worker)

        elif event.name == "CoreResCommand": # LLM 명령어 응답 도착
            msg, success = event.data
            
            success = LLMErrorCode.SUCCESS
            
            
            script, success = ResponseParser.parse_action_command(msg)
            if not success:
                script = {'plan': []}
            # print(script)
            self.event_hub.event.emit(AppEvent("UiResCommand", script))
        
        elif event.name == "CoreReqOper": # Operation 요청
            script_exe = ScriptExecuter()

            worker = Worker(lambda: script_exe.run_script(event.data), self.event_hub, "CoreResOper")
            self.thread_pool.start(worker)
            
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
            
            script_exe = ScriptExecuter()
            worker = Worker(lambda: script_exe.move(src, dest), self.event_hub, "CoreResMov")
            self.thread_pool.start(worker)
            
        elif event.name == "CoreResMov": # 명령 결과
            e = event.data
            self.event_hub.event.emit(AppEvent("UiResFile", e))
            if e:
                print("실패", e)
                return
            print("성공")

        elif event.name == "CoreFileAdd": # 파일 생성
            self.context_builder = ContextBuilder()
            system_msg, prompt = self.context_builder.format_move_prompt(file_path=event.data['src'], max_depth=1)

            llm_client = LLMClient()
            worker = Worker(lambda: llm_client.query(system_msg = system_msg, prompt = prompt), self.event_hub, "CoreFileAddRes")
            self.thread_pool.start(worker)

        elif event.name == "CoreFileAddRes":
            res, err = event.data
            res, err = ResponseParser.parse_action_move(res)

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