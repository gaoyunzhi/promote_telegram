#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import yaml
import asyncio
import plain_db
from datetime import datetime
import time
import sys
import random

existing = plain_db.load('existing')
group_log = {}
message_log = {}
message_loop = plain_db.load('message_loop')
added_time = plain_db.load('added_time')

for key, value in existing.items.items():
    target = key.split('=')[0]
    group_log[target] = max(group_log.get(target, 0), value)
    message = key[len(target) + 1:]
    message_log[message] = max(group_log.get(message, 0), value)

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('settings') as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

def getPeerId(peer_id):
    for method in [lambda x: x.channel_id, 
        lambda x: x.chat_id, lambda x: x.user_id]:
        try:
            return method(peer_id)
        except:
            ...

def shouldSend(messages, setting):
    for message in messages:
        # todo 法轮功的不算，那个鄂州亚太的不算
        if message.from_id and getPeerId(message.from_id) in [521358914, 771096498, 609517172, 1180078433]:
            continue
        if message.action:
            continue
        if time.time() - datetime.timestamp(message.date) < setting.get('wait_minute', 30) * 60:
            if 'debug' in sys.argv:
                print(message)
            return False # 不打断现有对话
    if time.time() - datetime.timestamp(messages[0].date) > 24 * 60 * 60:
        return True
    for message in messages[:5]:
        if message.from_id and getPeerId(message.from_id) == credential['user_id']:
            return False
    return True

def getTarget(target):
    target = target.split('(')[0]
    try:
        return int(target)
    except:
        return target

def getPromoteMessageHash(message):
    return '%s=%d=%d' % (message.split()[-1].split('/')[-1], datetime.now().month, int(datetime.now().day / 3))

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

async def log(client, group, posts):
    message = posts[0]
    if group.username:
        link = 'https://t.me/%s/%d' % (group.username, message.id)
    else:
        link = 'https://t.me/c/%s/%d' % (group.id, message.id)
    debug_group = await client.get_entity(credential['debug_group'])
    await client.send_message(debug_group, link)

async def process(client):
    targets = list(settings['groups'].items())
    random.shuffle(targets)
    for title, setting in targets:
        target = setting['id']
        if time.time() - group_log.get(str(target), 0) < setting.get('gap_hour', 5) * 60 * 60:
            continue
        if not added_time.get(target):
            added_time.update(target, int(time.time()))
        if time.time() - added_time.get(target) < 48 * 60 * 60: # 新加群不发言
            continue

        if 'debug' in sys.argv:
            print('fetching', target) 
        try:
            group =  await client.get_entity(target)
        except Exception as e:
            print('telegram_promote group fetching fail', target, str(e))
            if 'is private' in str(e):
                removeTarget(target)
                continue
            continue
        if 'debug' in sys.argv:
            username = group.username
            if username:
                username = 'https://t.me/' + username
            print(group.id, group.title, username)
        
        posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        
        if (not setting.get('debug')) and (not shouldSend(posts.messages, setting)):
            continue
        # if setting.get('debug'):
        #     print(group.id, group.title, 'shouldsend', shouldSend(posts.messages, setting))

        for subscription in setting.get('subscriptions', []):
            subscription = getTarget(subscription)
            channel =  await client.get_entity(subscription)
            posts = await client(GetHistoryRequest(peer=channel, limit=30,
                offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
            for post in posts.messages[:22]:
                if time.time() - datetime.timestamp(post.date) < 5 * 60 * 60:
                    continue
                item_hash = getHash(target, post)
                if time.time() - message_log.get(getMessageHash(post), 0) < 48 * 60 * 60:
                    continue
                if existing.get(item_hash):
                    continue
                post_ids = list(getPostIds(post, posts))
                try:
                    posts = await client.forward_messages(group, post_ids, channel)
                except Exception as e:
                    print(group.title, str(e))
                    continue
                await log(client, group, posts)
                print('promoted!', group.title)
                existing.update(item_hash, int(time.time()))
                return
        if not setting.get('promote_messages'):
            continue
        promote_messages = settings.get('promote_messages')
        loop_index = message_loop.get('promote_messages', 0) % len(promote_messages)
        message = promote_messages[loop_index]
        item_hash = '%s=%s' % (str(target), getPromoteMessageHash(message))
        if existing.get(item_hash):
            continue
        post = await client.send_message(group, message)
        await log(client, group, [post])
        message_loop.inc('promote_messages', 1)
        print('promoted!', group.title)
        existing.update(item_hash, int(time.time()))
        return

async def populateSetting(client):
    targets = list(settings['groups'].items())
    for target, setting in targets:
        if setting.get('id'):
            continue
        try:
            group = await client.get_entity(getTarget(target))
        except Exception as e:
            if 'is private' in str(e):
                del settings['groups'][target]
                with open('deleted_settings', 'a') as f:
                    deleted = {target: setting}
                    f.write(yaml.dump(deleted, sort_keys=True, indent=2, allow_unicode=True))
                    f.write('\n\n')
                continue
        setting['id'] = group.id
        if group.username:
            setting['username'] = group.username
        if 'joinchat' in target:
            setting['invitation_link'] = target
        name = group.title
        del settings['groups'][target]
        settings['groups'][name] = setting
    with open('settings', 'w') as f:
        f.write(yaml.dump(settings, sort_keys=True, indent=2, allow_unicode=True))


async def run():
    client = TelegramClient('session_file', credential['api_id'], credential['api_hash'])
    await client.start(password=credential['password'])
    await populateSetting(client)
    await process(client)
    await client.disconnect()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(run())
    loop.close()