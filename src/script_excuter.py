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
        if isinstance(value, list):
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

        if isinstance(rollback, list):
            self.rollback_list.extend(rollback)
        else:
            self.rollback_list.append(rollback)

    def run_script(self, script):
        try:
            for instruction in script:
                self.execute_instruction(instruction)
        except Exception as e:
            e = self.rollback()
            return str(e), e
        return None
    
    def move(self, source, destination):
        try:
            _, rollback = FileSystemManager.move(source, destination)
            self.rollback_list.append(rollback)
        except Exception as e:
            return str(e)
        return None
        
    def rollback(self):
        """
        rollback list를 받아 역순으로 실행시켜 주는 함수
        """
        for cmd in reversed(self.rollback_list):
            try:
                action = cmd['action']
                source = self.resolve(cmd['source'])
                destination = self.resolve(cmd['destination'])
                self.actions[action](source, destination)
            except Exception as e:
                return f"failed to rollback: {e}"