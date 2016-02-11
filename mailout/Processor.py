
class Processor:
    def __init__(self):
        pass

    def process(self, args, config):
        db = {}
        self.check_args(args)
        resources = self.select_resources(args, db, config)
        self.relate_to_recipients(args, resources, db, config)
        return db

    def select_resources(self, args, db, config):
        raise Exception('select_resources not implemented')

    def relate_to_recipients(self, args, resources, db, config):
        raise Exception('relate_to_recipients not implemented')

    def check_args(self):
        pass
    
    
