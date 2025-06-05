from filesystem_manager import FileSystemManager

class ScriptExecuter:
    def __init__(self):
        available_actions = FileSystemManager.get_actions()
        self.actions = dict()
        for a in available_actions:
            self.actions[a]=available_actions[a][0]
        self.symbols = {}

    def resolve(self, value):
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
            self.symbols[result] = self.actions[action](source, destination)
        else:
            self.actions[action](source, destination)

    def run_script(self, script):
        try:
            for instruction in script:
                self.execute_instruction(instruction)
        except Exception as e:
            return e.__str__
        return None