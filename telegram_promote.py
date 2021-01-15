#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import asyncio
from datetime import datetime
import time
import sys
import random
from telegram_util import matchKey
from settings import Settings
from cache import Cache
from helper import getClient, preProcess, getPostIds, getPeerId, getLink

S = Settings()
C = Cache()

def shouldSend(messages, setting):
    for message in messages:
        if S.isBlockedMessage(message):
            continue
        if message.action:
            continue
        if time.time() - datetime.timestamp(message.date) < setting.get('wait_minute', 30) * 60:
            if 'debug' in sys.argv:
                print('need wait due to message', setting['title'], message.raw_text[:20])
            return False # 不打断现有对话
    if time.time() - datetime.timestamp(messages[0].date) > 24 * 60 * 60:
        return True
    for message in messages[:5]:
        if message.from_id and getPeerId(message.from_id) in S.promote_user_ids:
            return False
    return True

def getPromoteMessageHash(message):
    return '%s=%d=%d' % (message.split()[-1].split('/')[-1], datetime.now().month, int(datetime.now().day / 3))

def getMessageHash(post):
    message_id = post.grouped_id
    if post.fwd_from:
        message_id = message_id or post.fwd_from.channel_post
        return '%s=%s' % (str(getPeerId(post.fwd_from.from_id)), str(message_id))
    message_id = message_id or post.id
    return '%d=%d' % (getPeerId(post.peer_id), message_id)

def getHash(target, post):
    return '%s=%s' % (str(target), getMessageHash(post))

async def log(client, group, posts):
    debug_group = await C.get_entity(client, S.credential['debug_group'])
    await client.send_message(debug_group, getLink(group, posts[0]))

async def logGroupPosts(client, group, group_posts):
    for message in group_posts.messages:
        if not matchKey(message.raw_text, S.watching_keys):
            continue
        if S.isBlockedMessage(message):
            continue
        item_hash = 'forward=' + ''.join(message.raw_text.split())[:30]
        if S.existing.get(item_hash):
            continue
        forward_group = await C.get_entity(client, S.credential['forward_group'])
        post_ids = list(getPostIds(message, group_posts.messages))
        await client.forward_messages(forward_group, post_ids, group)
        await client.send_message(forward_group, 'id: %d chat: %s' % (
            getPeerId(message.from_id), getLink(group, message)), link_preview=False)
        S.existing.update(item_hash, 1)

async def trySend(client, group, subscription, post):
    if time.time() - datetime.timestamp(post.date) < 5 * 60 * 60:
        return
    item_hash = getHash(group.id, post)
    if time.time() - S.message_log.get(getMessageHash(post), 0) < 12 * 60 * 60:
        return
    if S.existing.get(item_hash):
        return
    post_ids = list(getPostIds(post, C.getPostsCached(subscription)))
    try:
        results = await client.forward_messages(group, post_ids, C.getChannelCached(subscription))
    except Exception as e:
        print(group.title, str(e))
        return
    await log(client, group, results)
    S.existing.update(item_hash, int(time.time()))
    return True

async def process(clients):
    targets = list(S.groups.items())
    random.shuffle(targets)
    for gid, setting in targets:
        if not setting.get('promoter') or not setting.get('promoting'):
            continue
        print(setting['title'], S.shouldSendToGroup(gid, setting))
        if not S.shouldSendToGroup(gid, setting):
            continue

        client = getClient(clients, setting)
        try:
            group = await client.get_entity(gid)
        except Exception as e:
            print('telegram_promote Error group fetching fail', gid, setting, str(e))
            continue

        group_posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        if not setting.get('debug'):
            await logGroupPosts(client, group, group_posts)
        if (not setting.get('debug')) and (not shouldSend(group_posts.messages, setting)):
            continue

        if setting.get('keys'):
            for subscription in S.all_subscriptions:
                print(subscription)
                posts = await C.getPosts(client, subscription, S)
                for post in posts:
                    if not matchKey(post.raw_text, setting.get('keys')):
                        continue
                    result = await trySend(client, group, subscription, post)
                    if result:
                        return

        for subscription in setting.get('subscriptions', []):
            posts = await C.getPosts(client, subscription, S)
            for post in posts[:22]:
                result = await trySend(client, group, subscription, post)
                if result:
                    return
        if not setting.get('promote_messages'):
            continue
        message = S.getPromoteMessage()
        item_hash = '%s=%s' % (str(gid), getPromoteMessageHash(message))
        if S.existing.get(item_hash):
            continue
        result = await client.send_message(group, message)
        await log(client, group, [result])
        S.message_loop.inc('promote_messages', 1)
        S.existing.update(item_hash, int(time.time()))
        return

async def run():
    clients = {}
    for user, setting in S.credential['users'].items():
        client = TelegramClient('session_file_' + user, S.credential['api_id'], S.credential['api_hash'])
        await client.start(password=setting['password'])
        clients[user] = client
        await client.get_dialogs()
    await preProcess(clients, S.groups)
    await process(clients)
    for _, client in clients.items():
        await client.disconnect()
    
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(run())
    loop.close()