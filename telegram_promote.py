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
last_send = {}

for key, value in existing.items:
    target = int(key.split('_')[0])
    last_send[target] = max(last_send.get(target, 0), value)

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('settings') as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

def shouldSend(messages):
    if time.time() - datetime.timestamp(messages[0].date) < 30 * 60:
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

def getHash(target, post):
    return '%s_%d_%d' % (str(target), getPeerId(post.peer_id), post.id)

def getDialog(dialogs, group):
    for dialog in dialogs:
        print(getPeerId(dialog.peer_id))
        if getPeerId(dialog.peer_id) == group.id:
            return dialog

async def process(client):
    dialogs = await client.get_dialogs()

    for target, setting in settings.items():
        target = getTarget(target)
        if time.time() - last_send.get(target, 0) < 48 * 60 * 60: # start with 48 hour, see if I can change this to 5 hour
            continue

        group =  await client.get_entity(target)

        print('group', group.title)
        
        posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        
        if not shouldSend(posts.messages):
            continue

        for subscription in setting['subscriptions']:
            subscription = getTarget(subscription)
            channel =  await client.get_entity(subscription)
            posts = await client(GetHistoryRequest(peer=channel, limit=20,
                offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for post in posts.messages[::-1]:
                if time.time() - datetime.timestamp(post.date) < 5 * 60 * 60:
                    continue
                item_hash = getHash(target, post)
                if existing.get(item_hash):
                    continue
                dialog = getDialog(dialogs, group)
                await client.forward_messages(dialog, post)
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