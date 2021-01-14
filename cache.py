class Cache(object):
	def __init__(self):
		self.groups = {}
		self.posts = {}
		self.channels = {} 

	async def preprocess(clients, groups):
    	for target, setting in groups.items():
    		if setting.get('promoter'):
    			client = clients[setting.get('promoter')]
    		else:
    			client = next(iter(mydict.values()))
	        if setting.get('id'):
	            continue
	        try:
	            group = await client.get_entity(target)
	        except Exception as e:
	            if 'is private' in str(e):
	                del settings['groups'][target]
	                with open('deleted_settings', 'a') as f:
	                    deleted = {target: setting}
	                    f.write(yaml.dump(deleted, sort_keys=True, indent=2, allow_unicode=True))
	                continue
	            print('fetch failed', target, str(e))
	        setting['id'] = group.id
	        if group.username:
	            setting['username'] = group.username
	        if 'joinchat' in str(target):
	            setting['invitation_link'] = target
	        name = group.title
	        del settings['groups'][target]
	        if name not in settings['groups']:
	            settings['groups'][name] = setting
	        else:
	            print('Error! Group name conflict', name, setting)
	    with open('settings', 'w') as f:
	        f.write(yaml.dump(settings, sort_keys=True, indent=2, allow_unicode=True))

