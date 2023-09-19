

def create_actor(remote_actor):
    strategy = get_strategy(remote_actor)
    return Actor(strategy=strategy)


def get_strategy(remote_actor):
    if remote_actor['ident'] == 0:
        return 'GetFlag0'
    if remote_actor['ident'] == 1:
        return 'GetFlag1'
    if remote_actor['ident'] == 2:
        return 'GetFlag2'

