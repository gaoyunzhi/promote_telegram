#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import yaml
import asyncio
import plain_db
from datetime import datetime
import time

existing = plain_db.load('existing')
group_log = {}
message_log = {}

for key, value in existing.items.items():
    target = key.split('_')[0]
    group_log[target] = max(group_log.get(target, 0), value)
    message = key.[len(target) + 1:]
    print(message)
    message_log[message] = max(group_log.get(message, 0), value)

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('settings') as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

def shouldSend(messages):
    for message in messages:
        if message.from_id.user_id in [521358914]:
            continue
        if time.time() - datetime.timestamp(message.date) < 30 * 60:
            return False # 不打断现有对话
    if time.time() - datetime.timestamp(messages[0].date) > 48 * 60 * 60:
        return True
    for message in messages:
        if message.from_id.user_id == credential['user_id']:
            return False
    return True

def getTarget(target):
    target = target.split('(')[0]
    try:
        return int(target)
    except:
        return target

def getPeerId(peer_id):
    for method in [lambda x: x.channel_id, 
        lambda x: x.chat_id, lambda x: x.user_id]:
        try:
            return method(peer_id)
        except:
            ...

def getMessageHash(post):
    return '%d_%d' % (getPeerId(post.peer_id), post.id)

def getHash(target, post):
    return '%s_%s' % (str(target), getMessageHash(post))

async def process(client):
    # dialogs = await client.get_dialogs() # this may not be needed

    for target, setting in settings.items():
        target = getTarget(target)
        if time.time() - group_log.get(str(target), 0) < 48 * 60 * 60: # start with 48 hour, see if I can change this to 5 hour
            continue

        group =  await client.get_entity(target)
        
        posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        
        if not shouldSend(posts.messages):
            continue

        for subscription in setting.get('subscriptions', []):
            subscription = getTarget(subscription)
            channel =  await client.get_entity(subscription)
            posts = await client(GetHistoryRequest(peer=channel, limit=20,
                offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for post in posts.messages[::-1]:
                if time.time() - datetime.timestamp(post.date) < 5 * 60 * 60:
                    continue
                print(post)
                item_hash = getHash(target, post)
                if time.time() - message_log.get(getMessageHash(post), 0) < 48 * 60 * 60:
                    continue
                if existing.get(item_hash):
                    continue
                dialog = getDialog(dialogs, group)
                # TODO: see if change dialog.entity to group is ok
                await client.forward_messages(group, post.id, channel)
                existing.update(item_hash, int(time.time()))
                return

async def run():
    client = TelegramClient('session_file', credential['api_id'], credential['api_hash'])
    await client.start(password=credential['password'])

    await process(client)

    await client.disconnect()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(run())
    loop.close()