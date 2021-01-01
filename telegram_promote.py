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
message_loop = plain_db.load('message_loop')

for key, value in existing.items.items():
    target = key.split('=')[0]
    group_log[target] = max(group_log.get(target, 0), value)
    message = key[len(target) + 1:]
    message_log[message] = max(group_log.get(message, 0), value)

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('settings') as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

def shouldSend(messages):
    for message in messages:
        # todo 法轮功的不算，那个鄂州亚太的不算
        if message.from_id and message.from_id.user_id in [521358914]:
            continue
        if time.time() - datetime.timestamp(message.date) < 30 * 60:
            print(message)
            return False # 不打断现有对话
    if time.time() - datetime.timestamp(messages[0].date) > 48 * 60 * 60:
        return True
    print('here')
    for message in messages:
        if message.from_id and message.from_id.user_id == credential['user_id']:
            return False
    print('here1')
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
    message_id = post.grouped_id
    if post.fwd_from:
        message_id = message_id or post.fwd_from.channel_post
        return '%d=%s' % (getPeerId(post.fwd_from.from_id), str(message_id))
    message_id = message_id or post.id
    return '%d=%d' % (getPeerId(post.peer_id), message_id)

def getHash(target, post):
    return '%s=%s' % (str(target), getMessageHash(post))

def getPostIds(target_post, posts):
    if target_post.grouped_id:
        for post in posts.messages[::-1]:
            if post.grouped_id == target_post.grouped_id:
                yield post.id
    else:
        yield target_post.id

async def process(client):
    for target, setting in settings['groups'].items():
        target = getTarget(target)
        if time.time() - group_log.get(str(target), 0) < setting.get('gap_hour', 5) * 60 * 60:
            continue

        group =  await client.get_entity(target)
        print(group.id, group.title)
        
        posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        
        if (not setting.get('debug')) and (not shouldSend(posts.messages)):
            continue
        if setting.get('debug'):
            print(group.id, group.title, 'shouldsend', shouldSend(posts.messages))

        for subscription in setting.get('subscriptions', []):
            subscription = getTarget(subscription)
            channel =  await client.get_entity(subscription)
            posts = await client(GetHistoryRequest(peer=channel, limit=30,
                offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for post in posts.messages[::-1][:22]:
                if time.time() - datetime.timestamp(post.date) < 5 * 60 * 60:
                    continue
                item_hash = getHash(target, post)
                if time.time() - message_log.get(getMessageHash(post), 0) < 48 * 60 * 60:
                    continue
                if existing.get(item_hash):
                    continue
                post_ids = list(getPostIds(post, posts))
                await client.forward_messages(group, post_ids, channel)
                existing.update(item_hash, int(time.time()))
                return
        if not setting.get('promote_messages'):
            continue
        promote_messages = settings.get('promote_messages')
        message = promote_messages[message_loop.get('promote_messages', 0) % len(promote_messages)]
        await client.send_message(group, message)
        message_loop.inc('promote_messages', 1)
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