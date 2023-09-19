import actor_strategies.actors
import structlog
import ascifight.computations as computations

logger = structlog.get_logger()

SERVER = "http://sessionstation.de/"
logger = structlog.get_logger()

TEAM = "EverythingsAwesome"
PASSWORD = "VFRules"

def create_actor(remote_actor, client):
    strategy = get_strategy(remote_actor, client)
    logger.info('Creating actor for remote actor', remote_actor=remote_actor['ident'])
    return actor_strategies.actors.Actor(strategy=strategy, actor_id=remote_actor['ident'])

def get_strategy(remote_actor, client):
    if remote_actor['ident'] == 0:
        return GetFlagStrategy(target='TimeOut', client=client)
    elif remote_actor['ident'] == 1:
        return GetFlagStrategy(target='Superdetractors', client=client)
    elif remote_actor['ident'] == 2:
        return GetFlagStrategy(target='ByteMe', client=client)


class GetFlagStrategy:
    def __init__(self, target: str, client):
        self.target = target
        self.client = client

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
                issue_order(client=self.client,order="grabput", actor_id=actor["ident"], direction=direction)
            # if we are not there yet we need to go
            else:
                issue_order(client=self.client, order="move", actor_id=actor["ident"], direction=direction)
        # if it has the flag we need to head home
        else:
            # where is home?
            direction = compute_direction(
                origin=actor_coordinates, target=home_coordinates
            )[0]

            # if we are already just 1 space apart we are there
            if compute_distance(origin=actor_coordinates, target=home_coordinates) == 1:
                # we put the flag on our base
                issue_order(order="grabput", actor_id=actor["ident"], direction=direction)
            else:
                # if we are not there we slog on home
                issue_order(order="move", actor_id=actor["ident"], direction=direction)


def to_coordinates(input_coords: dict):
    return computations.Coordinates(x=input_coords['x'], y=input_coords['y'])


def compute_direction(origin, target) -> list[computations.Directions]:
    return computations.calc_target_coordinate_direction(to_coordinates(origin), to_coordinates(target))


def compute_distance(origin, target) -> int:
    return computations.distance(to_coordinates(origin), to_coordinates(target))


def issue_order(client, order: str, actor_id: str, direction: computations.Directions):
    logger.info("Issuing order", order=order, actor_id=actor_id, direction=direction)
    client.post(
        url=f"{SERVER}orders/{order}/{actor_id}",
        params={"direction": direction.value},
        auth=(TEAM, PASSWORD),
    )