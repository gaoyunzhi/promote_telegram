#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
import yaml
import asyncio
import plain_db

existing = plain_db.loadKeyOnlyDB('existing')

with open('credential') as f:
    credential = yaml.load(f, Loader=yaml.FullLoader)

with open('settings') as f:
    settings = yaml.load(f, Loader=yaml.FullLoader)

async def run():
	client = TelegramClient('session_file', credential['api_id'], credential['api_hash'])
    await client.start(password=credential['password'])
    dialogs = await client.get_dialogs()
    print('dialogs', dialogs)
    print('dialogs[3]', dialogs[3])

    for target in settings:
    	channel_entity=await client.get_entity(target)
    	posts = await client(GetHistoryRequest(peer=channel_entity, limit=10,
        	offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
    	print(posts[0])
    	 
    await client.disconnect()

if __name__ == "__main__":
	loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    r = loop.run_until_complete(run())
    loop.close()