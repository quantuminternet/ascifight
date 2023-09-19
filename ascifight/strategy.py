import actor_strategies.actors
import structlog
import ascifight.computations as computations
import ascifight.pathfinding as pathfinding
import ascifight.util

logger = structlog.get_logger()

SERVER = "http://sessionstation.de/"
logger = structlog.get_logger()

TEAM = "EverythingsAwesome"
PASSWORD = "VFRulez"

def create_actor(remote_actor, client, game_state):
    strategy = get_strategy(remote_actor, client, game_state)
    logger.info('Creating actor for remote actor', remote_actor=remote_actor['ident'])
    return actor_strategies.actors.Actor(strategy=strategy, actor_id=remote_actor['ident'], client=client)


def get_strategy(remote_actor, client, game_state):
    if remote_actor['type'] == 'Runner':
        home_basecoords = [base for base in game_state['bases'] if base['team'] == TEAM][0]['coordinates']
        dist_dict = {}
        for flag in game_state['bases']:
            if flag['team'] != TEAM:
                target_coordinates = flag['coordinates']
                dist_dict[flag['team']] = compute_distance(origin=home_basecoords, target=target_coordinates)

        sorted_targets = list(dict(sorted(dist_dict.items(), key=lambda item: item[1])).keys())
        if remote_actor['ident'] == 0:
            return GetFlagStrategy(target=sorted_targets[0], client=client, actor_id=remote_actor['ident'])
        elif remote_actor['ident'] == 1:
            return GetFlagStrategy(target=sorted_targets[1], client=client, actor_id=remote_actor['ident'])

    elif remote_actor['type'] == 'Attacker':
        if remote_actor['ident'] == 1:
            return AttackEnemyStrategy(client=client, actor_id=remote_actor['ident'])
        elif remote_actor['ident'] == 2:
            return AttackEnemyStrategy(client=client, actor_id=remote_actor['ident'])
        elif remote_actor['ident'] == 3:
            return AttackEnemyStrategy(client=client, actor_id=remote_actor['ident'])

    elif remote_actor['type'] == 'Destroyer':
        return DestroyerStrategy(client=client, actor_id=remote_actor['ident'])


class GetFlagStrategy:
    def __init__(self, target: str, client, actor_id: int):
        self.target = target
        self.client = client
        self.actor_id = actor_id

    def execute(self, gamestate: dict, rules: dict):
        # this teams flag we want to get
        target_team = self.target
        # this is the base we need to go to, assuming their flag is there?
        target_flag = [flag for flag in gamestate["flags"] if flag["team"] == target_team][0]
        # these are the flags coordinates
        target_coordinates = target_flag["coordinates"]
        # this is our base
        home_base = [base for base in gamestate["bases"] if base["team"] == 'EverythingsAwesome'][0]
        # we need the coordinates when we want to go home
        home_coordinates = home_base["coordinates"]

        actor = [actor for actor in gamestate["actors"] if actor["team"] == 'EverythingsAwesome'][self.actor_id]
        actor_coordinates = actor["coordinates"]
        # if it doesn't have the flag it needs to go to the enemy base
        if not actor["flag"]:
            # we can calculate the direction of the enemy base or get it from the server
            direction = pathfinding.find_path(game_state=gamestate, rules=rules, actor_id=self.actor_id,
                                              target=to_coordinates(target_coordinates), team=TEAM)

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
            direction = pathfinding.find_path(game_state=gamestate, rules=rules, actor_id=self.actor_id,
                                              target=to_coordinates(home_coordinates), team=TEAM)

            # if we are already just 1 space apart we are there
            if compute_distance(origin=actor_coordinates, target=home_coordinates) == 1:
                # we put the flag on our base
                issue_order(order="grabput", actor_id=actor["ident"], direction=direction, client=self.client)
            else:
                # if we are not there we slog on home
                issue_order(order="move", actor_id=actor["ident"], direction=direction, client=self.client)


class AttackEnemyStrategy:

    def __init__(self, client, actor_id: int):
        self.client = client
        self.actor_id = actor_id

    def execute(self, gamestate: dict, rules: dict):
        actor = [actor for actor in gamestate["actors"] if actor["team"] == 'EverythingsAwesome'][self.actor_id]
        actor_coordinates = actor["coordinates"]

        if self.actor_id == 1:
            target_coordinates = ascifight.util.get_nearest_enemy_coordinates(game_state=gamestate,
                                                                          team='EverythingsAwesome',
                                                                          enemyteam='ByteMe',
                                                                          actor_id=actor["ident"],
                                                                          actor_type='Runner')
        elif self.actor_id == 2:
            target_coordinates = ascifight.util.get_nearest_enemy_coordinates(game_state=gamestate,
                                                                              team='EverythingsAwesome',
                                                                              enemyteam='Superdetractors',
                                                                              actor_id=actor["ident"],
                                                                              actor_type='Runner')
        elif self.actor_id == 3:
            target_coordinates = ascifight.util.get_nearest_enemy_coordinates(game_state=gamestate,
                                                                              team='EverythingsAwesome',
                                                                              enemyteam='Superdetractors',
                                                                              actor_id=actor["ident"],
                                                                              actor_type='Attacker')

        direction = pathfinding.find_path(game_state=gamestate, rules=rules, actor_id=self.actor_id,
                                          target=target_coordinates, team=TEAM)

        logger.info('Attacker finding target', actor=actor_coordinates, target=target_coordinates)

        if compute_distance(origin=actor_coordinates,
                            target={'x': target_coordinates.x, 'y': target_coordinates.y}) == 1:
            # If we are next to an enemy, attack again for good measure

            logger.info('Attacker attacking')
            ascifight.strategy.issue_order(order="attack",
                                           actor_id=actor["ident"],
                                           direction=direction,
                                           client=self.client)
        else:
            issue_order(client=self.client, order="move", actor_id=actor["ident"], direction=direction)


class AttackAreaStrategy:

    def __init__(self, client, actor_id: int, target: dict, distance: int = 3):
        self.client = client
        self.actor_id = actor_id
        self.distance = distance
        self.target = target

    def execute(self, gamestate: dict, rules: dict):
        actor = [actor for actor in gamestate["actors"] if actor["team"] == 'EverythingsAwesome'][self.actor_id]
        actor_coordinates = actor["coordinates"]
        targets = [actor for actor in gamestate["actors"] if actor["team"] != TEAM
                   and abs(self.target["x"] - actor_coordinates["y"]) <= self.distance
                   and abs(self.target["y"] - actor_coordinates["y"]) <= self.distance]
        if targets:
            target = sorted(targets,
                            key=lambda enemy: computations.distance(to_coordinates(enemy['coordinates']),
                                                                   to_coordinates(actor_coordinates)),
                            reverse=True)[0]["coordinates"]
        else:
            target = self.target
        target_coordinates = to_coordinates(target)
        direction = pathfinding.find_path(game_state=gamestate, rules=rules, actor_id=self.actor_id,
                                          target=target_coordinates, team=TEAM)
        if compute_distance(origin=actor_coordinates,
                            target={'x': target_coordinates.x, 'y': target_coordinates.y}) == 1:
            # If we are next to an enemy, attack again for good measure
            ascifight.strategy.issue_order(order="destroy",
                                           actor_id=actor["ident"],
                                           direction=direction,
                                           client=self.client)
        else:
            issue_order(client=self.client, order="move", actor_id=actor["ident"], direction=direction)


class DestroyerStrategy:

    def __init__(self, client, actor_id: int):
        self.client = client
        self.actor_id = actor_id

    def execute(self, gamestate: dict, rules: dict):
        actor = [actor for actor in gamestate["actors"] if actor["team"] == 'EverythingsAwesome'][self.actor_id]
        actor_coordinates = actor["coordinates"]
        target_coordinates = [base for base in gamestate["bases"] if base["team"] == 'EverythingsAwesome'][0]['coordinates']
        direction = pathfinding.find_path(game_state=gamestate, rules=rules, actor_id=self.actor_id,
                                          target=to_coordinates(target_coordinates), team=TEAM)

        distance = computations.distance(to_coordinates(actor_coordinates), to_coordinates(target_coordinates))
        if distance > 1:
            issue_order(client=self.client, order="move", actor_id=actor["ident"], direction=direction)




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