#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import yaml
import asyncio
import plain_db
from datetime import datetime
import time

existing = plain_db.loadKeyOnlyDB('existing')

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('settings') as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

def shouldSend(messages):
    print(datetime.timestamp(messages[0].date))
    print(time.time())
    for message in messages:
        ...
    return False


async def run():
    client = TelegramClient('session_file', credential['api_id'], credential['api_hash'])
    await client.start(password=credential['password'])

    for target in settings:
        target = target.split('(')[0]
        group=await client.get_entity(int(target))
        print('group', group, group.id)
        posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        
        if not shouldSend(posts.messages):
            continue
        print('posts.messages[0]', posts.messages[0])

    await client.disconnect()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(run())
    loop.close()