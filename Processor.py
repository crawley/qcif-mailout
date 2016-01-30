
class Processor:
    def __init__(self):
        pass

    def process(self, args, config):
        db = {}
        self.check_args(args)
        resources = self.select_resources(args, db, config)
        users = self.related_users(args, resources, db, config)
        return users, db

    def select_resources(self, args, db, config):
        raise Exception('select_resources not implemented')

    def related_users(self, args, resources, db, config):
        raise Exception('related_users not implemented')

    def check_args(self):
        pass
    
    
