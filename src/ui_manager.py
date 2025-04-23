import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import os
from typing import List, Dict, Any, Callable, Optional


class UIManager:
    """
    그래픽 사용자 인터페이스(GUI) 요소들을 관리하고 사용자와의 상호작용을 처리합니다.
    """

    def __init__(self, core_controller):
        """
        GUI 구성 요소들을 초기화하고 FileManagerCore에 대한 참조를 저장합니다.

        Args:
            core_controller: FileManagerCore의 인스턴스
        """
        self.core_controller = core_controller
        self.root = None
        self.main_frame = None
        self.status_var = None
        self.nl_input_var = None
        self.watched_dirs_listbox = None
        self.history_listbox = None

    def display_main_window(self):
        """메인 애플리케이션 창을 표시합니다."""
        # tkinter 루트 윈도우 생성
        self.root = tk.Tk()
        self.root.title("SmartFileManager")
        self.root.geometry("800x600")

        # 스타일 설정
        style = ttk.Style()
        style.theme_use("default")  # 'clam', 'alt', 'default', 'classic' 등 사용 가능

        # 메인 프레임
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 상단 프레임 (자연어 명령 입력)
        command_frame = ttk.LabelFrame(self.main_frame, text="자연어 명령", padding=5)
        command_frame.pack(fill=tk.X, pady=5)

        self.nl_input_var = tk.StringVar()
        nl_entry = ttk.Entry(command_frame, textvariable=self.nl_input_var, width=50)
        nl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        submit_button = ttk.Button(
            command_frame, text="실행", command=self.on_submit_command
        )
        submit_button.pack(side=tk.RIGHT)

        # 중앙 프레임 (나눔)
        center_frame = ttk.Frame(self.main_frame)
        center_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 왼쪽 프레임 (감시 디렉토리)
        dirs_frame = ttk.LabelFrame(center_frame, text="감시 중인 디렉토리", padding=5)
        dirs_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        self.watched_dirs_listbox = tk.Listbox(dirs_frame)
        self.watched_dirs_listbox.pack(fill=tk.BOTH, expand=True)

        dirs_button_frame = ttk.Frame(dirs_frame)
        dirs_button_frame.pack(fill=tk.X, pady=5)

        add_dir_button = ttk.Button(
            dirs_button_frame, text="추가", command=self._add_watch_directory
        )
        add_dir_button.pack(side=tk.LEFT, padx=(0, 5))

        remove_dir_button = ttk.Button(
            dirs_button_frame, text="제거", command=self._remove_watch_directory
        )
        remove_dir_button.pack(side=tk.LEFT)

        # 오른쪽 프레임 (작업 기록)
        history_frame = ttk.LabelFrame(center_frame, text="작업 기록", padding=5)
        history_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.history_listbox = tk.Listbox(history_frame)
        self.history_listbox.pack(fill=tk.BOTH, expand=True)

        history_button_frame = ttk.Frame(history_frame)
        history_button_frame.pack(fill=tk.X, pady=5)

        undo_button = ttk.Button(
            history_button_frame, text="실행 취소", command=self.on_undo_click
        )
        undo_button.pack(side=tk.LEFT)

        # 하단 프레임 (상태 표시)
        status_frame = ttk.Frame(self.main_frame)
        status_frame.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="준비")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT)

        settings_button = ttk.Button(
            status_frame, text="설정", command=self._show_settings
        )
        settings_button.pack(side=tk.RIGHT)

        # 창이 닫힐 때 처리
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

        # 메인 루프 시작
        self.root.mainloop()

    def prompt_for_confirmation(self, action_description: str, options: list) -> str:
        """
        제안된 작업(예: 파일 이동 제안)을 표시하고 사용자의 선택을 반환합니다.

        Args:
            action_description: 사용자에게 보여줄 작업 설명
            options: 사용자에게 제공할 선택 옵션들

        Returns:
            사용자가 선택한 옵션
        """
        # 대화 상자 생성
        dialog = tk.Toplevel(self.root)
        dialog.title("작업 확인")
        dialog.geometry("500x300")
        dialog.transient(self.root)  # 부모 창에 종속
        dialog.grab_set()  # 포커스 가져오기

        # 설명 레이블
        desc_label = ttk.Label(dialog, text=action_description, wraplength=480)
        desc_label.pack(pady=10, padx=10, anchor=tk.W)

        # 선택 변수
        selected_option = tk.StringVar()

        # 옵션 프레임
        option_frame = ttk.Frame(dialog)
        option_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # 옵션 버튼 생성
        for i, option in enumerate(options):
            option_text = option
            if isinstance(option, dict) and "path" in option and "reason" in option:
                option_text = f"{option['path']} - {option['reason']}"

            radio = ttk.Radiobutton(
                option_frame, text=option_text, value=str(i), variable=selected_option
            )
            radio.pack(anchor=tk.W, pady=3)

        # 기본 선택
        if options:
            selected_option.set("0")

        # 버튼 프레임
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        result = [None]  # 결과를 저장할 리스트 (비로컬 캡처를 위해)

        # 확인 버튼
        def on_confirm():
            idx = int(selected_option.get()) if selected_option.get() else 0
            if 0 <= idx < len(options):
                result[0] = options[idx]
            dialog.destroy()

        confirm_button = ttk.Button(button_frame, text="확인", command=on_confirm)
        confirm_button.pack(side=tk.RIGHT, padx=10)

        # 취소 버튼
        def on_cancel():
            result[0] = None
            dialog.destroy()

        cancel_button = ttk.Button(button_frame, text="취소", command=on_cancel)
        cancel_button.pack(side=tk.RIGHT)

        # 대화 상자가 닫힐 때까지 대기
        dialog.wait_window()

        # 선택된 옵션 반환
        if result[0] is not None:
            return result[0]
        return None

    def display_results(self, message: str):
        """
        성공 또는 오류 메시지를 보여줍니다.

        Args:
            message: 표시할 메시지
        """
        self.status_var.set(message)
        messagebox.showinfo("결과", message)

    def get_nl_input(self) -> str:
        """
        자연어 명령을 입력받는 필드를 제공합니다.

        Returns:
            사용자가 입력한 자연어 명령
        """
        return self.nl_input_var.get()

    def display_settings_dialog(self, current_settings: dict) -> dict:
        """
        설정을 보거나 편집할 수 있는 대화 상자를 표시합니다.

        Args:
            current_settings: 현재 설정값

        Returns:
            업데이트된 설정값
        """
        # 설정 대화 상자 생성
        dialog = tk.Toplevel(self.root)
        dialog.title("설정")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 일반 설정 탭
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="일반")

        # LLM 설정 탭
        llm_frame = ttk.Frame(notebook, padding=10)
        notebook.add(llm_frame, text="LLM API")

        # UI 설정 탭
        ui_frame = ttk.Frame(notebook, padding=10)
        notebook.add(ui_frame, text="UI")

        # 파일 작업 탭
        file_ops_frame = ttk.Frame(notebook, padding=10)
        notebook.add(file_ops_frame, text="파일 작업")

        # 설정 값을 담을 변수
        settings_vars = {
            "llm": {
                "api_key": tk.StringVar(
                    value=current_settings.get("llm", {}).get("api_key", "")
                ),
                "model_name": tk.StringVar(
                    value=current_settings.get("llm", {}).get("model_name", "gpt-4")
                ),
                "temperature": tk.DoubleVar(
                    value=current_settings.get("llm", {}).get("temperature", 0.7)
                ),
            },
            "ui": {
                "theme": tk.StringVar(
                    value=current_settings.get("ui", {}).get("theme", "system")
                ),
                "language": tk.StringVar(
                    value=current_settings.get("ui", {}).get("language", "ko")
                ),
                "show_notifications": tk.BooleanVar(
                    value=current_settings.get("ui", {}).get("show_notifications", True)
                ),
            },
            "file_operations": {
                "max_history": tk.IntVar(
                    value=current_settings.get("file_operations", {}).get(
                        "max_history", 20
                    )
                ),
                "create_backup_before_move": tk.BooleanVar(
                    value=current_settings.get("file_operations", {}).get(
                        "create_backup_before_move", True
                    )
                ),
                "skip_hidden_files": tk.BooleanVar(
                    value=current_settings.get("file_operations", {}).get(
                        "skip_hidden_files", True
                    )
                ),
            },
        }

        # LLM 설정 필드
        ttk.Label(llm_frame, text="API 키:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(
            llm_frame, textvariable=settings_vars["llm"]["api_key"], width=30, show="*"
        ).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(llm_frame, text="모델:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(
            llm_frame,
            textvariable=settings_vars["llm"]["model_name"],
            values=["gpt-4", "gpt-3.5-turbo"],
        ).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(llm_frame, text="Temperature:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        ttk.Scale(
            llm_frame, variable=settings_vars["llm"]["temperature"], from_=0.0, to=1.0
        ).grid(row=2, column=1, sticky=tk.W, padx=5)

        # UI 설정 필드
        ttk.Label(ui_frame, text="테마:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(
            ui_frame,
            textvariable=settings_vars["ui"]["theme"],
            values=["system", "light", "dark"],
        ).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(ui_frame, text="언어:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Combobox(
            ui_frame, textvariable=settings_vars["ui"]["language"], values=["ko", "en"]
        ).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(ui_frame, text="알림 표시:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        ttk.Checkbutton(
            ui_frame, variable=settings_vars["ui"]["show_notifications"]
        ).grid(row=2, column=1, sticky=tk.W, padx=5)

        # 파일 작업 설정 필드
        ttk.Label(file_ops_frame, text="최대 기록 수:").grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        ttk.Spinbox(
            file_ops_frame,
            from_=5,
            to=100,
            textvariable=settings_vars["file_operations"]["max_history"],
            width=5,
        ).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(file_ops_frame, text="이동 전 백업 생성:").grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        ttk.Checkbutton(
            file_ops_frame,
            variable=settings_vars["file_operations"]["create_backup_before_move"],
        ).grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(file_ops_frame, text="숨김 파일 무시:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        ttk.Checkbutton(
            file_ops_frame,
            variable=settings_vars["file_operations"]["skip_hidden_files"],
        ).grid(row=2, column=1, sticky=tk.W, padx=5)

        # 버튼 프레임
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        result = [None]

        # 확인 버튼
        def on_confirm():
            updated_settings = {
                "llm": {
                    "api_key": settings_vars["llm"]["api_key"].get(),
                    "model_name": settings_vars["llm"]["model_name"].get(),
                    "temperature": settings_vars["llm"]["temperature"].get(),
                },
                "ui": {
                    "theme": settings_vars["ui"]["theme"].get(),
                    "language": settings_vars["ui"]["language"].get(),
                    "show_notifications": settings_vars["ui"][
                        "show_notifications"
                    ].get(),
                },
                "file_operations": {
                    "max_history": settings_vars["file_operations"][
                        "max_history"
                    ].get(),
                    "create_backup_before_move": settings_vars["file_operations"][
                        "create_backup_before_move"
                    ].get(),
                    "skip_hidden_files": settings_vars["file_operations"][
                        "skip_hidden_files"
                    ].get(),
                },
            }

            # watched_directories 설정 보존
            if "watched_directories" in current_settings:
                updated_settings["watched_directories"] = current_settings[
                    "watched_directories"
                ]

            result[0] = updated_settings
            dialog.destroy()

        confirm_button = ttk.Button(button_frame, text="확인", command=on_confirm)
        confirm_button.pack(side=tk.RIGHT, padx=10)

        # 취소 버튼
        cancel_button = ttk.Button(button_frame, text="취소", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT)

        # 대화 상자가 닫힐 때까지 대기
        dialog.wait_window()

        # 업데이트된 설정 반환
        return result[0] or current_settings

    def display_path_suggestions(self, file_path: str, suggestions: list[str]):
        """
        특정 파일에 대해 LLM이 제안한 경로 목록을 보여줍니다.

        Args:
            file_path: 대상 파일 경로
            suggestions: 제안된 경로 목록
        """
        # 파일 정보 표시
        file_info = f"파일: {os.path.basename(file_path)}\n경로: {file_path}"
        suggestion_descriptions = []

        for suggestion in suggestions:
            if (
                isinstance(suggestion, dict)
                and "path" in suggestion
                and "reason" in suggestion
            ):
                suggestion_descriptions.append(
                    f"{suggestion['path']} - {suggestion['reason']}"
                )
            else:
                suggestion_descriptions.append(str(suggestion))

        selected = self.prompt_for_confirmation(
            f"{file_info}\n\n다음 위치로 이동하시겠습니까?", suggestions
        )

        if selected:
            # 사용자가 선택한 대상 경로로 이동 작업 실행
            destination = selected
            if isinstance(selected, dict) and "path" in selected:
                destination = selected["path"]

            operation = {
                "action": "move",
                "source": file_path,
                "destination": os.path.join(destination, os.path.basename(file_path)),
            }

            self.core_controller.execute_file_operation(operation)

    def display_action_plan(self, plan: list[dict]):
        """
        복잡한 작업의 단계들을 보여줍니다.

        Args:
            plan: 실행할 작업 단계
        """
        if not plan:
            messagebox.showinfo("작업 계획", "실행할 작업이 없습니다.")
            return

        # 대화 상자 생성
        dialog = tk.Toplevel(self.root)
        dialog.title("작업 계획")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # 상단 레이블
        ttk.Label(
            dialog, text="다음 작업을 실행하시겠습니까?", font=("Helvetica", 12)
        ).pack(pady=10)

        # 스크롤 가능한 프레임
        frame_canvas = ttk.Frame(dialog)
        frame_canvas.pack(fill=tk.BOTH, expand=True, padx=10)

        canvas = tk.Canvas(frame_canvas)
        scrollbar = ttk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 작업 목록 표시
        for i, action in enumerate(plan):
            action_type = action.get("action", "unknown")
            description = action.get("description", "")

            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, pady=5)

            action_text = ""
            if action_type == "move":
                source = action.get("source", "")
                destination = action.get("destination", "")
                action_text = f"이동: '{source}' → '{destination}'"
            elif action_type == "rename":
                path = action.get("path", "")
                new_name = action.get("new_name", "")
                action_text = f"이름 변경: '{path}' → '{new_name}'"
            elif action_type == "delete":
                path = action.get("path", "")
                action_text = f"삭제: '{path}'"
            elif action_type == "create_directory":
                path = action.get("path", "")
                action_text = f"디렉토리 생성: '{path}'"
            else:
                action_text = f"알 수 없는 작업: {action_type}"

            ttk.Label(frame, text=f"{i+1}. {action_text}", wraplength=550).pack(
                anchor=tk.W
            )

            if description:
                ttk.Label(
                    frame,
                    text=f"   이유: {description}",
                    wraplength=550,
                    foreground="gray",
                ).pack(anchor=tk.W)

        # 버튼 프레임
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        # 확인 버튼
        def on_execute():
            dialog.destroy()
            # 계획 실행
            result = self.core_controller.execute_file_operation({"plan": plan})
            if result:
                self.display_results("작업이 성공적으로 완료되었습니다.")
            else:
                self.display_results("작업 실행 중 오류가 발생했습니다.")

        execute_button = ttk.Button(button_frame, text="실행", command=on_execute)
        execute_button.pack(side=tk.RIGHT, padx=10)

        # 취소 버튼
        cancel_button = ttk.Button(button_frame, text="취소", command=dialog.destroy)
        cancel_button.pack(side=tk.RIGHT)

        # 대화 상자가 닫힐 때까지 대기
        dialog.wait_window()

    # 이벤트 핸들러/콜백 함수들
    def on_submit_command(self):
        """사용자가 자연어 명령을 제출했을 때 호출됩니다."""
        command = self.get_nl_input()
        if command:
            self.status_var.set(f"명령 처리 중: {command}")
            self.nl_input_var.set("")  # 입력 필드 초기화
            self.core_controller.handle_natural_language_command(command)

    def on_accept_suggestion(self):
        """사용자가 제안을 수락했을 때 호출됩니다."""
        pass  # prompt_for_confirmation에서 처리됨

    def on_undo_click(self):
        """사용자가 실행 취소 버튼을 클릭했을 때 호출됩니다."""
        self.status_var.set("마지막 작업 취소 중...")
        result = self.core_controller.undo_last_operation()
        if result:
            self.display_results("작업이 성공적으로 취소되었습니다.")
        else:
            self.display_results("작업을 취소할 수 없습니다.")

    def update_watched_directories(self, directories):
        """
        감시 중인 디렉토리 목록을 업데이트합니다.

        Args:
            directories: 디렉토리 경로 목록
        """
        if self.watched_dirs_listbox:
            self.watched_dirs_listbox.delete(0, tk.END)
            for directory in directories:
                self.watched_dirs_listbox.insert(tk.END, directory)

    def update_history(self, history):
        """
        작업 기록 목록을 업데이트합니다.

        Args:
            history: 작업 기록 목록
        """
        if self.history_listbox:
            self.history_listbox.delete(0, tk.END)
            for item in history:
                action_type = item.get("action", "")
                timestamp = item.get("timestamp", "").split("T")[0]

                if action_type == "move":
                    source = os.path.basename(item.get("source", ""))
                    destination = os.path.dirname(item.get("destination", ""))
                    self.history_listbox.insert(
                        0, f"{timestamp} 이동: {source} → {destination}"
                    )
                elif action_type == "rename":
                    path = item.get("path", "")
                    new_name = item.get("new_name", "")
                    self.history_listbox.insert(
                        0,
                        f"{timestamp} 이름 변경: {os.path.basename(path)} → {new_name}",
                    )
                elif action_type == "delete":
                    path = item.get("path", "")
                    self.history_listbox.insert(
                        0, f"{timestamp} 삭제: {os.path.basename(path)}"
                    )
                else:
                    self.history_listbox.insert(0, f"{timestamp} {action_type}")

    def _add_watch_directory(self):
        """디렉토리 선택 대화 상자를 표시하고 선택한 디렉토리를 감시 목록에 추가합니다."""
        directory = filedialog.askdirectory(title="감시할 디렉토리 선택")
        if directory:
            self.core_controller.add_watch_directory(directory)

    def _remove_watch_directory(self):
        """선택한 디렉토리를 감시 목록에서 제거합니다."""
        selected = self.watched_dirs_listbox.curselection()
        if selected:
            directory = self.watched_dirs_listbox.get(selected[0])
            self.core_controller.remove_watch_directory(directory)

    def _show_settings(self):
        """설정 대화 상자를 표시합니다."""
        current_settings = self.core_controller.get_settings()
        updated_settings = self.display_settings_dialog(current_settings)
        if updated_settings and updated_settings != current_settings:
            self.core_controller.update_settings(updated_settings)

    def _on_closing(self):
        """창이 닫힐 때 호출됩니다."""
        self.core_controller.stop()
        self.root.destroy()
