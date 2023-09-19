import actor_strategies.actors
import structlog


logger = structlog.get_logger()


def create_actor(remote_actor):
    strategy = get_strategy(remote_actor)
    logger.info('Creating actor for remote actor', remote_actor=remote_actor['ident'])
    return actor_strategies.actors.Actor(strategy=strategy, actor_id=remote_actor['ident'])


def get_strategy(remote_actor):
    if remote_actor['ident'] == 0:
        return GetFlagStrategy(target='TimeOut')
    elif remote_actor['ident'] == 1:
        return GetFlagStrategy(target='Superdetractors')
    elif remote_actor['ident'] == 2:
        return GetFlagStrategy(target='ByteMe')


class GetFlagStrategy:
    def __init__(self, target: str):
        self.target = target

    def execute(self, gamestate):
        # this teams flag we want to get
        target_team = self.target
        # this is the base we need to go to, assuming their flag is there?
        target_base = [base for base in gamestate["bases"] if base["team"] == target_team][0]
        # these are the bases coordinates
        target_coordinates = target_base["coordinates"]
        # this is our base
        home_base = [base for base in gamestate["bases"] if base["team"] == 'EverythingsAwesome'][0]
        # we need the coordinates when we want to go home
        home_coordinates = home_base["coordinates"]
        # we will just use the first of our actors we have
        # assuming that it will be able to grab the flag
        actor = [actor for actor in gamestate["actors"] if actor["team"] == 'EverythingsAwesome'][0]
        # thats where the actor currently is
        actor_coordinates = actor["coordinates"]
        # if it doesn't have the flag it needs to go to the enemy base
        if not actor["flag"]:
            # we can calculate the direction of the enemy base or get it from the server
            direction = compute_direction(
                origin=actor_coordinates, target=target_coordinates
            )[0]
            # we need to stop if we are standing right next to the base
            if compute_distance(origin=actor_coordinates, target=target_coordinates) == 1:
                # and grab the flag, the direction is the one we would have walked to
                issue_order(order="grabput", actor_id=actor["ident"], direction=direction)
            # if we are not there yet we need to go
            else:
                issue_order(order="move", actor_id=actor["ident"], direction=direction)
        # if it has the flag we need to head home
        else:
            # where is home?
            direction = compute_direction(
                origin=actor_coordinates, target=home_coordinates
            )[0]


