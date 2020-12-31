#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import yaml
import asyncio

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

async def findLinksAsync(source):
    client = TelegramClient('session_file', credential['api_id'], credential['api_hash'])
    await client.start(password=credential['password'])
    channel_entity=await client.get_entity(source)
    posts = await client(GetHistoryRequest(peer=channel_entity, limit=30, # change to 30
        offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
    await client.disconnect()
    return posts

def findLinks(source):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(findLinksAsync(source))
    loop.close()
    links = {}
    for message in r.messages:
        try:
            message.media.webpage
            message.media.webpage.title
        except:
            continue
        links[tuple([item.url for item in message.entities])] = (
            message.media.webpage.title[11:-21]).strip()
        if len(links) == 8:
            return links
    return links

def run():
	...

if __name__ == "__main__":
	run()