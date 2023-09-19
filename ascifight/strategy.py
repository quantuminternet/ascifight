import actor_strategies.actors
import structlog


logger = structlog.get_logger()


def create_actor(remote_actor):
    strategy = get_strategy(remote_actor)
    logger.info('Creating actor for remote actor', remote_actor=remote_actor['ident'])
    return actor_strategies.actors.Actor(strategy=strategy, actor_id=remote_actor['ident'])


def get_strategy(remote_actor):
    if remote_actor['ident'] == 0:
        return 'GetFlag0'
    if remote_actor['ident'] == 1:
        return 'GetFlag1'
    if remote_actor['ident'] == 2:
        return 'GetFlag2'

