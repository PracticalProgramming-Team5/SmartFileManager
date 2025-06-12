from PyQt5.QtCore import QObject, QThreadPool, QMetaObject, pyqtSlot, QReadWriteLock
from event_hub import EventHub, AppEvent, Worker

from settings_manager import SettingsManager
from llm_client import LLMClient, LLMErrorCode
from context_builder import ContextBuilder
from response_parser import ResponseParser
from directory_monitor import DirectoryMonitor
from script_excuter import ScriptExecuter
from history_manager import HistoryManager
from filesystem_manager import FileSystemManager
from tagdb import FileTagDB
from time import strftime
from typing import List

class WrapDirectoryMonitor(QObject):
    def __init__(self):
        super().__init__()
        self.event_hub = EventHub.get_global_instance()
        def parse_monitor(src, dst, code):
            name, data = "", {}
            if code == 0:
                self.event_hub.add_monitored.emit(src)
            elif code == 1:
                self.event_hub.del_monitored.emit(src)
            else:
                self.event_hub.move_monitored.emit(src, dst)
        self.dir_monitor = DirectoryMonitor(parse_monitor)
        QMetaObject.connectSlotsByName(self)

    def start(self):
        dirs_monitor = set(SettingsManager.get('monitoring_dirs'))
        dirs_available = set(SettingsManager.get('available_dirs'))

        for dir in dirs_monitor | dirs_available:
            self.dir_monitor.add_directory(dir)
        self.dir_monitor.start()
    def stop(self):
        self.dir_monitor.stop()


class FileManagerCore(QObject):
    def __init__(self):
        super().__init__()
        self.event_hub = EventHub.get_global_instance()
        self.setObjectName("core")
        # self.event_hub.event.connect(self.__process_event)
        self.runnable = False
        self.tag_db = FileTagDB()
        
        self.dir_monitor = WrapDirectoryMonitor()
        self.thread_pool = QThreadPool()

        self.event_hub.started_from_ui.connect(self.on_started_from_ui)
        self.event_hub.stopped_from_ui.connect(self.on_stopped_from_ui)
        self.event_hub.command_requested_from_ui.connect(self.on_command_requested_from_ui)
        self.event_hub.command_responded_from_llm.connect(self.on_command_responded_from_llm)
        self.event_hub.operation_requested_from_ui.connect(self.on_operation_requested_from_ui)
        self.event_hub.operation_responded_from_script.connect(self.on_operation_responded_from_script)
        self.event_hub.suggestion_accepted_from_ui.connect(self.on_suggestion_accepted_from_ui)
        self.event_hub.move_responded_from_script.connect(self.on_move_responded_from_script)
        self.event_hub.suggestion_responded_from_llm.connect(self.on_suggestion_responded_from_llm)
        self.event_hub.add_monitored.connect(self.on_add_monitored)
        self.event_hub.move_monitored.connect(self.on_move_monitored)
        self.event_hub.del_monitored.connect(self.on_del_monitored)
        self.event_hub.undo_requested_from_ui.connect(self.on_undo_requested_from_ui)
        self.event_hub.history_requested_from_ui.connect(self.on_history_requested_from_ui)

        self.intersested_commands = []
        self.available_commands = []

        self.mutex_history = QReadWriteLock()
        self.mutex_llm = QReadWriteLock()
    # @pyqtSlot()
    def on_started_from_ui(self):
        print('start')
        self.runnable = True
        self.intersested_commands = SettingsManager.get("interest_commands")
        self.available_commands = SettingsManager.get("available_commands")
        self.dir_monitor.start()
        self.event_hub.state_responded_from_core.emit(self.runnable)


    # @pyqtSlot()
    def on_stopped_from_ui(self):
        print('stop')
        self.runnable = False
        self.intersested_commands = []
        self.available_commands = []
        self.dir_monitor.stop()
        self.__clear()
        self.event_hub.state_responded_from_core.emit(self.runnable)

    # @pyqtSlot(str)
    def on_command_requested_from_ui(self, command: str):
        if not self.runnable:
            return
        def query():
            self.context_builder = ContextBuilder()
            system_msg, prompt = self.context_builder.format_command_prompt(command)
            llm_client = LLMClient()
            # msg, e = llm_client.query(system_msg = system_msg, prompt = prompt)
            # print(msg)
            msg, e = sample_msg, LLMErrorCode.SUCCESS
            
            self.event_hub.command_responded_from_llm.emit(e, msg)
        
        worker = Worker(query, self.mutex_llm, True)
        self.thread_pool.start(worker)


    def on_command_responded_from_llm(self, e: LLMErrorCode, message: str):
        if not self.runnable:
            return
        err, action, explanation, feature = True, [], "", ""

        if not e == LLMErrorCode.SUCCESS:
            explanation = f"API 통신중 에러가 발생하였습니다.\n{list(e)}"
        else:
            script, success = ResponseParser.parse_action_command(message)
            if success:
                action, explanation = script['plan'], script['explanation']
                interst = "\n    -".join([act['action'] for act in action if act['action'] in self.intersested_commands])
                forbidden = "\n    -".join([act['action'] for act in action if not act['action'] in self.available_commands])
                err = False
                if interst:
                    feature += f"다음의 관심 명령어가 사용되었습니다. \n    -{interst}"
                if forbidden:
                    feature += f"다음의 금지 명령어가 사용되었습니다. \n    -{forbidden}"
                    err = True # 금지 명령어는 안나올 듯.

            else:
                explanation = "명령어 해석중 오류가 발생하였습니다."
        
        self.event_hub.command_responded_from_core.emit(err, action, explanation, feature)

    # @pyqtSlot(list, str)
    def on_operation_requested_from_ui(self, action: list, explanation: str):
        if not self.runnable:
            return
        def run_script():
            script_exe = ScriptExecuter()
            e = script_exe.run_script(action)
            if e is None:
                err, message = False, "명령어 실행이 완료되었습니다."
                HistoryManager.log({
                    "date": strftime('%y.%m.%d-%H:%M'),
                    "exe": script_exe,
                    "explanation": explanation
                })
                self.event_hub.history_responded_from_core.emit(HistoryManager.get())
            else:
                err, message = True, f"명령어 실행 중 오류가 발생하였습니다. {e}"
            self.event_hub.operation_responded_from_script.emit(err, message)
        worker = Worker(run_script, self.mutex_history, True)
        self.thread_pool.start(worker)
    
    # @pyqtSlot
    def on_operation_responded_from_script(self, err: bool, message: str):
        if not self.runnable:
            return
        self.event_hub.operation_responded_from_core.emit(err, message)

    # @pyqtSlot
    def on_suggestion_accepted_from_ui(self, src: List[str], dest: str):
        if not self.runnable:
            return
        def move():
            script_exe = ScriptExecuter()
            e = script_exe.move(src, dest)
            if e is None:
                err, message = False, "명령어 실행이 완료되었습니다."
                list_src ='\n'.join(src)
                HistoryManager.log({
                    "date": strftime('%y.%m.%d-%H:%M'),
                    "exe": script_exe,
                    "explanation": f"{list_src} \n-> {dest}"
                })
                self.event_hub.history_responded_from_core.emit(HistoryManager.get())
            else:
                err, message = True, f"명령어 실행 중 오류가 발생하였습니다. {e}"
            self.event_hub.move_responded_from_script.emit(err, message)

        worker = Worker(move, self.mutex_history, True)
        self.thread_pool.start(worker)

    # @pyqtSlot
    def on_move_responded_from_script(self, err: bool, message: str):
        if not self.runnable:
            return
        self.event_hub.suggestion_opperated_from_core.emit(err, message)
    
    # @pyqtSlot
    def on_suggestion_responded_from_llm(self, e: LLMErrorCode, message: str):
        if not self.runnable:
            return
        err, src, recommend, reason = True, "", [], []

        if not e == LLMErrorCode.SUCCESS:
            src = f"API 통신중 에러가 발생하였습니다.\n{list(e)}"
        else:
            res, success = ResponseParser.parse_action_move(message)

            if success:
                src = res['source']
                recommend = list(res['destination'])
                reason = list(res['explanation'])
                tags = res['tags']
                err = False
                self.tag_db.add_file(file_path=src, tags=tags)
            else:
                src = "파일 이동 실패."
        self.event_hub.suggestion_responded_from_core.emit(err, src, recommend, reason)
    
    # @pyqtSlot
    def on_add_monitored(self, path: str):
        if not self.runnable:
            return
        # if not self.l:
        #     return
        def query():
            self.context_builder = ContextBuilder()
            system_msg, prompt = self.context_builder.format_move_prompt(file_path=path, max_depth=1)

            llm_client = LLMClient()
            # msg, e = llm_client.query(system_msg = system_msg, prompt = prompt)
            msg, e = sample_msg2, LLMErrorCode.SUCCESS
            self.event_hub.suggestion_responded_from_llm.emit(e, msg)
        worker = Worker(query, self.mutex_llm, True)
        self.thread_pool.start(worker)


    # @pyqtSlot
    def on_move_monitored(self, src: str, dst: str):
        if not self.runnable:
            return
        self.tag_db.rename_file(old_path=src, new_path=dst)

    # @pyqtSlot
    def on_del_monitored(self, src: str):
        if not self.runnable:
            return
        self.tag_db.delete_file(file_path=src)
    
    def on_undo_requested_from_ui(self):
        def undo():
            lastest = HistoryManager.peek()
            if lastest is None:
                return
            e = lastest["exe"].rollback()
            err, msg = False, f"다음 작업이 취소되었습니다: [{lastest['explanation']}]"

            if e is None:
                HistoryManager.pop()
            else:
                err, msg = True, f"작업 취소중 에러가 발생했습니다: {e}"
            self.event_hub.undo_responded_from_core.emit(err, msg)
            self.event_hub.history_responded_from_core.emit(HistoryManager.get())
        worker = Worker(undo, self.mutex_history, True)
        self.thread_pool.start(worker)

    def on_history_requested_from_ui(self):
        worker = Worker(lambda: self.event_hub.history_responded_from_core.emit(HistoryManager.get()), self.mutex_history)
        self.thread_pool.start(worker)
        
        
    def __clear(self):
        FileSystemManager.clean_temp()

sample_msg = """```json
{
  "plan": [
    {
      "action": "ls",
      "source": "/Users/ssw/Documents/test/다운로드",
      "destination": "N",
      "result": "download_files"
    },
    {
      "action": "mask_filename",
      "source": "download_files",
      "destination": ".ppt",
      "result": "ppt_files"
    },
    {
      "action": "move",
      "source": "ppt_files",
      "destination": "/Users/ssw/Documents/test/다운로드/휴지통",
      "result": ""
    }
  ],
  "explanation": "다운로드 폴더의 모든 피피티 파일을 휴지통 폴더로 이동합니다."
}
```"""

sample_msg2 = """```json
{
  "source": "/Users/ssw/Documents/test/다운로드/데이터프로그래밍발표.pdf",
  "tags": [
    "데이터프로그래밍",
    "발표",
    "학생명단",
    "학번",
    "수업자료",
    "PDF",
    "2025",
    "교육",
    "프레젠테이션",
    "강의"
  ],
  "destination": [
    "/Users/ssw/Documents/test/학교 수업/실전코딩",
    "/Users/ssw/Documents/test/학교 수업/네트워크",
    "/Users/ssw/Documents/test/학교 수업/운영체제"
  ],
  "explanation": [
    "/Users/ssw/Documents/test/학교 수업/실전코딩을 추천하는 이유: 데이터프로그래밍과 관련된 발표 자료로 실전코딩 수업과 관련이 깊습니다.",
    "/Users/ssw/Documents/test/학교 수업/네트워크를 추천하는 이유: 데이터와 네트워크 관련 수업 자료로 활용될 수 있습니다.",
    "/Users/ssw/Documents/test/학교 수업/운영체제를 추천하는 이유: 운영체제 수업에서도 데이터프로그래밍 관련 발표 자료가 유용할 수 있습니다."
  ]
}
```"""