from filesystem_manager import FileSystemManager

class ScriptExecuter:
    """
    스크립트를 실행시키고 롤백을 관리하는 클래스

    **주의: 한 작업 명령당 하나의 객체를 생성하여 관리해야 합니다.**
    """
    def __init__(self):
        available_actions = FileSystemManager.get_actions()
        self.actions = dict()
        for a in available_actions:
            self.actions[a]=available_actions[a][0]
        self.symbols = {}
        self.rollback_list = []

    def resolve(self, value):
        if isinstance(value, list) or isinstance(value, tuple):
            return [self.resolve(v) for v in value]
        
        if value in self.symbols:
            return self.symbols[value]
        return value

    def execute_instruction(self, instruction):
        action = instruction['action']
        source = self.resolve(instruction['source'])
        destination = self.resolve(instruction['destination'])
        result = instruction['result']

        if action not in self.actions:
            raise ValueError(f"Unknown action: {action}")
        
        if result:
            self.symbols[result], rollback = self.actions[action](source, destination)
        else:
            _, rollback = self.actions[action](source, destination)

        # miner patch: None 들어가면 rollback 실패. 임시로 None 이면 추가 안하도록 수정.
        if rollback is None:
            return
        
        if isinstance(rollback, list) or isinstance(rollback, tuple):
            self.rollback_list.extend(rollback)
        else:
            self.rollback_list.append(rollback)

    def run_script(self, script):
        """
        FS script를 실행합니다.
        """
        try:
            for instruction in script:
                self.execute_instruction(instruction)
        except Exception as e:
            self.rollback()
            return str(e)
        return None
    
    def move(self, source, destination):
        """
        추천된 경로로 파일을 이동합니다.
        """
        try:
            _, rollback = FileSystemManager.move(source, destination)
            
            # 복수 파일 롤백시 롤백 리스트 이중으로 중첩되던 문제.
            if isinstance(rollback, list) or isinstance(rollback, tuple):
                self.rollback_list.extend(rollback)
            else:
                self.rollback_list.append(rollback)
        except Exception as e:
            return str(e)
        return None
        
    def rollback(self):
        """
        실행한 작업을 되돌리는 함수
        """
        for cmd in reversed(self.rollback_list):
            try:
                print(cmd)
                action = cmd['action']
                source = self.resolve(cmd['source'])
                destination = self.resolve(cmd['destination'])
                self.actions[action](source, destination)
            except Exception as e:
                return f"failed to rollback: {e}"