import plain_db
import yaml
import time
from helper import getPeerId
from telegram_util import matchKey, isCN

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
        self.all_subscriptions = self.settings.get('all_subscriptions')
        self.watching_keys = self.settings.get('watching_keys')
        self.block_keys = self.settings.get('block_keys')
        self.block_ids = self.settings.get('block_ids')
        self.mute_channel_id = self.settings.get('mute_channel_id')
        self.no_forward_ids = self.settings.get('no_forward_ids')
        self.default_client_name = self.settings.get('default_client_name')
        self.promote_user_ids = [item['id'] for item in self.credential['users'].values()]
        self.promote_messages = self.settings.get('promote_messages')

    def _populateExisting(self):
        self.group_log = {}
        self.message_log = {}
        for key, value in self.existing.items.items():
            target = key.split('=')[0]
            self.group_log[target] = max(self.group_log.get(target, 0), value)
            message = key[len(target) + 1:]
            self.message_log[message] = max(self.message_log.get(message, 0), value)

    def shouldSendToGroup(self, gid, setting):
        if time.time() - self.group_log.get(str(gid), 0) < setting.get('gap_hour', 12) * 60 * 60:
            return False
        if not self.added_time.get(gid):
            self.added_time.update(gid, int(time.time()))
        return time.time() - self.added_time.get(gid) > 48 * 60 * 60 # 新加群不发言

    def isBlockedMessage(self, message):
        if matchKey(message.raw_text, self.block_keys):
            return True
        if message.from_id and getPeerId(message.from_id) in (self.block_ids + list(self.promote_user_ids)):
            return True
        if message.fwd_from and getPeerId(message.fwd_from.from_id) in self.block_ids:
            return True
        return False

    def isNoForwardMessage(self, message):
        if not message.from_id:
            return True
        if getPeerId(message.from_id) in self.no_forward_ids:
            return True
        if message.fwd_from and getPeerId(message.fwd_from.from_id) in self.no_forward_ids:
            return True
        return False

    def getPromoteMessage(self):
        loop_index = self.message_loop.get('promote_messages', 0) % len(self.promote_messages)
        return self.promote_messages[loop_index]

    def matchLanguage(self, subscription, post):
        if not self.settings.get('chinese_only').get(subscription):
            return True
        return isCN(post.message)

    def shouldExclude(self, post):
        return matchKey(str(post), ['关于评论区', 
            '多莉·帕顿', '我将大声疾呼女权主义重要性',
            '自己穿上假屌', '假屌是可拆卸'])

    async def populateIdMap(self, client, subscription):
        channel = await client.get_entity(subscription)
        self.settings['id_map'][subscription] = channel.id
        self.save()

    def save(self):
        with open('settings.yaml', 'w') as f:
            f.write(yaml.dump(self.settings, sort_keys=True, indent=2, allow_unicode=True))