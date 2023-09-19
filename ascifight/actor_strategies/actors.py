import abc
import random

class Strategy(abc.ABC):

    @abc.abstractmethod
    def execute(self, gamestate):
        raise NotImplementedError


class GetFlagStrategy(Strategy):

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

class Actor:
    def __init__(self, strategy: str, actor_id: int):
        self.actor_id = actor_id
        self.strategy = self.construct_strategy(strategy=strategy)

    def construct_strategy(self, strategy: str) -> Strategy:
        strategy_dict = {}
        return strategy_dict.get(strategy)

    def make_attack(self):
        directions = ['left', 'right', 'top', 'bottom']
        direction = random.choice(directions)
        #issue_order(order="attack", actor_id=self.actor_id, direction=direction)

    def destroy_walls(self):
        pass

    def execute(self, gamestate):
        self.make_attack()
        self.destroy_walls()
        self.strategy.execute(gamestate=gamestate)

