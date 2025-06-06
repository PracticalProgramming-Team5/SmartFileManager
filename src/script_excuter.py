from filesystem_manager import FileSystemManager

class ScriptExecuter:
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
            self.rollback()
            return str(e)
        return None
    
    def rollback(self):
        for cmd in reversed(self.rollback_list):
            try:
                action = cmd['action']
                source = self.resolve(cmd['source'])
                destination = self.resolve(cmd['destination'])
                self.actions[action](source, destination)
            except Exception as e:
                return f"failed to rollback: {e}"