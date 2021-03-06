#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest, SearchRequest
from telethon.tl.types import InputMessagesFilterEmpty
import asyncio
from datetime import datetime
import time
import sys
import random
from telegram_util import matchKey
from settings import Settings
from cache import Cache
from helper import getClient, addMute, preProcess, getPostIds, getPeerId, getDisplayLink, getLink

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

def getLogMessage(group, message, client_name):
    id_info, fwd_info, client_info = '', '', ''
    msg_id = getPeerId(message.from_id)
    if msg_id:
        id_info = 'id: %d ' % msg_id
    fwd_from = message.fwd_from and getPeerId(message.fwd_from.from_id)
    if fwd_from:
        fwd_info = 'fwd_id: %d ' % fwd_from
    if client_name != S.default_client_name:
        client_info = '%s ' % client_name
    return '%s%s%schat: %s' % (
        id_info,
        fwd_info,
        client_info,
        getDisplayLink(group, message, S.groups))

async def logGroupPosts(client, group, group_posts, client_name):
    for message in group_posts.messages:
        if not matchKey(message.raw_text, S.watching_keys):
            continue
        if S.isBlockedMessage(message):
            continue
        if S.isNoForwardMessage(message):
            continue
        item_hash = 'forward=' + ''.join(message.raw_text.split())[:30]
        if S.existing.get(item_hash):
            continue
        forward_group = await C.get_entity(client, S.credential['forward_group'])
        post_ids = list(getPostIds(message, group_posts.messages))
        await client.forward_messages(forward_group, post_ids, group)
        await client.send_message(forward_group, 
            getLogMessage(group, message, client_name), link_preview=False)
        S.existing.update(item_hash, 1)

async def trySend(client, group, subscription, post):
    if time.time() - datetime.timestamp(post.date) < 5 * 60 * 60:
        return
    item_hash = getHash(group.id, post)
    if time.time() - S.message_log.get(getMessageHash(post), 0) < 12 * 60 * 60:
        return
    if S.existing.get(item_hash):
        return
    if not S.matchLanguage(subscription, post):
        return
    if S.shouldExclude(post):
        return
    post_ids = list(getPostIds(post, C.getPostsCached(subscription)))
    channel = await C.getChannel(client, subscription, S)
    S.existing.update(item_hash, -1)
    try:
        results = await client.forward_messages(group, post_ids, channel)
    except Exception as e:
        print('telegram_promote forward fail', group.title, subscription, post_ids, str(e))
        return
    print('promoted!', group.title)
    await log(client, group, results)
    S.existing.update(item_hash, int(time.time()))
    return True

async def process(clients):
    targets = list(S.groups.items())
    random.shuffle(targets)
    for gid, setting in targets:
        if setting.get('kicked'):
            continue
        client_name, client = getClient(clients, setting)
        try:
            group = await client.get_entity(gid)
        except Exception as e:
            print('telegram_promote Error group fetching fail', gid, setting, str(e))
            continue

        group_posts = await client(GetHistoryRequest(peer=group, limit=10,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
        if not setting.get('debug'):
            await logGroupPosts(client, group, group_posts, client_name)
        if (not setting.get('promoter') or not setting.get('promoting') or 
            not S.shouldSendToGroup(gid, setting)):
            continue
        if (not setting.get('debug')) and (not shouldSend(group_posts.messages, setting)):
            continue

        if setting.get('keys'):
            for subscription in S.all_subscriptions:
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

        if setting.get('subscriptions'):
            print('nothing to promote: ' + group.title)

        if not setting.get('promote_messages'):
            continue
        message = S.getPromoteMessage()
        item_hash = '%s=%s' % (str(gid), getPromoteMessageHash(message))
        if S.existing.get(item_hash):
            continue
        result = await client.send_message(group, message)
        print('promoted!', group.title)
        await log(client, group, [result])
        S.message_loop.inc('promote_messages', 1)
        S.existing.update(item_hash, int(time.time()))
        return

async def run():
    clients = {}
    for user, setting in S.credential['users'].items():
        client = TelegramClient('session_file_' + user, S.credential['api_id'], S.credential['api_hash'])
        await client.start(password=setting.get('password'))
        clients[user] = client
        await client.get_dialogs()
    await addMute(clients[S.default_client_name], S)
    await preProcess(clients, S.groups)
    await process(clients)
    for _, client in clients.items():
        await client.disconnect()

def passFilter(text):
    return True
    # if not text:
    #     return False
    # if '堕胎' in text:
    #     return True
    # if '国' in text and '女' in text:
    #     return True
    # return False

async def dialogs():
    user = 'lani'
    setting = S.credential['users'][user]
    client = TelegramClient('session_file_' + user, S.credential['api_id'], S.credential['api_hash'])
    await client.start(password=setting.get('password'))
    result = await client.get_dialogs()
    for group in result:
        try:
            group.entity.participants_count
        except:
            continue
        if 0 < group.entity.participants_count < 200 or group.entity.id in S.groups.keys():
            continue
        username = None
        try:
            username = group.entity.username
        except:
            ...
        print(group.title, group.id, username)
    await client.disconnect()

async def search():
    user = 'lani'
    setting = S.credential['users'][user]
    client = TelegramClient('session_file_' + user, S.credential['api_id'], S.credential['api_hash'])
    await client.start(password=setting.get('password'))
    result = await client.get_dialogs()
    user = await client.get_entity(1331301717)
    for item in result:
        group = await client.get_entity(item.id)
        filter = InputMessagesFilterEmpty()
        try:
            result = await client(SearchRequest(
                peer=group,     # On which chat/conversation
                q='',           # What to search for
                filter=filter,  # Filter to use (maybe filter for media)
                min_date=None,  # Minimum date
                max_date=None,  # Maximum date
                offset_id=0,    # ID of the message to use as offset
                add_offset=0,   # Additional offset
                limit=1,       # How many results
                max_id=0,       # Maximum message ID
                min_id=0,       # Minimum message ID
                from_id=user,
                hash=0
            ))
        except:
            continue
        username = None
        try:
            username = group.username
        except:
            ...
        for message in result.messages:
            if passFilter(message.raw_text):
                print(getLink(group, message), message.raw_text[:30].replace('\n', ' '))
    await client.disconnect()
    
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(run())
    loop.close()