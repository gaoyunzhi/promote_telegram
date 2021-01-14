def getClient(clients, setting):
    if setting.get('promoter'):
        return clients[setting.get('promoter')]
    return next(iter(mydict.values()))

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
            print('Error preProcess group fetch fail', gid, setting)
        if group.username:
            setting['username'] = group.username
        if 'joinchat' in str(gid):
            setting['invitation_link'] = gid
        setting['title'] = group.title
        del settings['groups'][gid]
        groups[group.id] = setting
        with open('groups', 'w') as f:
            f.write(yaml.dump(groups, sort_keys=True, indent=2, allow_unicode=True))
