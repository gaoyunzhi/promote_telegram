from telethon.tl.functions.messages import GetHistoryRequest

class Cache(object):
    def __init__(self):
        self.posts = {}
        self.entities = {}
        self.channels = {}

    async def get_entity(self, client, eid):
        if eid not in self.entities:
            self.entities[eid] = await client.get_entity(eid)
        return self.entities[eid]

    async def getPosts(self, client, subscription, S):
        if subscription not in self.posts:
            if subscription not in S.settings['id_map']:
                await S.populateIdMap(client, subscription)
            self.channels[subscription] = await self.get_entity(client, S.settings['id_map'][subscription])
            self.posts[subscription] = await client(GetHistoryRequest(peer=self.channels[subscription], limit=30,
                offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            self.posts[subscription] = self.posts[subscription].messages
        return self.posts[subscription]

    def getPostsCached(self, subscription):
        return self.posts[subscription]

    def getChannelCached(self, subscription):
        return self.channels[subscription]




    