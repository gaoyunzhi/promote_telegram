import yaml
from telethon.tl.functions.messages import GetHistoryRequest

def getClient(clients, setting):
    client_name = setting.get('promoter') or next(iter(clients.keys()))
    return client_name, clients[client_name]

def getPostIds(target_post, posts):
    if target_post.grouped_id:
        for post in posts[::-1]:
            if post.grouped_id == target_post.grouped_id:
                yield post.id
    else:
        yield target_post.id

def getLink(group, message):
    if group.username:
        return 'https://t.me/%s/%d' % (group.username, message.id)
    return 'https://t.me/c/%s/%d' % (group.id, message.id)

def getDisplayLink(group, message, groups):
    invitation_link = groups[group.id].get('invitation_link')
    suffix = ''
    if invitation_link:
        suffix = ' [进群](%s)' % invitation_link
    return '[%s](%s)%s' % (group.title, getLink(group, message), suffix)

def getPeerId(peer_id):
    for method in [lambda x: x.channel_id, 
        lambda x: x.chat_id, lambda x: x.user_id]:
        try:
            return method(peer_id)
        except:
            ...

async def addMute(client, S):
    channel = await client.get_entity(S.mute_channel_id)
    group_posts = await client(GetHistoryRequest(peer=group, limit=30,
            offset_date=None, offset_id=0, max_id=0, min_id=0, add_offset=0, hash=0))
    count = 0
    for message in group_posts.messages:
        try:
            mute_id = int(message.raw_text)
        except:
            continue
        if mute_id not in S.no_forward_ids:
            S.no_forward_ids.append(mute_id)
            count += 1
    S.save()
    if count: 
        await client.send_message(channel, 'mute id added: ' + str(count))

async def preProcess(clients, groups):
    for gid, setting in list(groups.items()):
        try:
            int(gid)
            continue
        except:
            ...
        _, client = getClient(clients, setting)
        group = await client.get_entity(gid)
        if group.username:
            setting['username'] = group.username
        if 'joinchat' in str(gid):
            setting['invitation_link'] = gid
        setting['title'] = group.title
        del groups[gid]
        groups[group.id] = setting
        with open('groups.yaml', 'w') as f:
            f.write(yaml.dump(groups, sort_keys=True, indent=2, allow_unicode=True))