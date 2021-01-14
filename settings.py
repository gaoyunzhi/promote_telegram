import plain_db
import yaml

class Settings(object):
    def __init__(self):
        self.existing = plain_db.load('existing')
        self.message_loop = plain_db.load('message_loop')
        self.added_time = plain_db.load('added_time')
        self._populateExisting()
        with open('credential') as f:
            self.credential = yaml.load(f, Loader=yaml.FullLoader)
        with open('settings.yaml') as f:
            self.settings = yaml.load(f, Loader=yaml.FullLoader)
        with open('groups.yaml') as f:
            self.groups = yaml.load(f, Loader=yaml.FullLoader)
        self._populateSubscription()

    def _populateExisting(self):
        self.group_log = {}
        self.message_log = {}
        for key, value in self.existing.items.items():
            target = key.split('=')[0]
            self.group_log[target] = max(self.group_log.get(target, 0), value)
            message = key[len(target) + 1:]
            self.message_log[message] = max(self.message_log.get(message, 0), value)

    def _populateSubscription(self):
        self.all_subscriptions = set()
        for _, setting in self.groups.items():
            for subscription in setting.get('subscriptions', []):
                self.all_subscriptions.add(subscription)