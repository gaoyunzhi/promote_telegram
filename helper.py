def getClient(clients, setting):
    if setting.get('promoter'):
        return clients[setting.get('promoter')]
    return next(iter(mydict.values()))

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

def getPeerId(peer_id):
    for method in [lambda x: x.channel_id, 
        lambda x: x.chat_id, lambda x: x.user_id]:
        try:
            return method(peer_id)
        except:
            ...

async def preProcess(clients, groups):
    for gid, setting in list(groups.items()):
        try:
            int(gid)
            continue
        except:
            ...
        client = getClient(clients, setting)
        try:
            group = await client.get_entity(gid)
        except:
            print('telegram_promote Error preProcess group fetch fail', gid, setting)
        if group.username:
            setting['username'] = group.username
        if 'joinchat' in str(gid):
            setting['invitation_link'] = gid
        setting['title'] = group.title
        del settings['groups'][gid]
        groups[group.id] = setting
        with open('groups', 'w') as f:
            f.write(yaml.dump(groups, sort_keys=True, indent=2, allow_unicode=True))
