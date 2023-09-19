import random

import ascifight.strategy
import ascifight.computations as computations
import ascifight.util


class Actor:
    def __init__(self, strategy, actor_id: int, client):
        self.actor_id = actor_id
        self.client = client
        self.strategy = strategy

    def make_attack(self, gamestate):
        nearest_enemy_directions = ascifight.util.get_nearest_enemy_direction(game_state=gamestate,
                                                                              team="EverythingsAwesome",
                                                                              actor_id=self.actor_id)
        direction = random.choice(nearest_enemy_directions)
        ascifight.strategy.issue_order(order="attack", actor_id=self.actor_id, direction=direction, client=self.client)

    def destroy_walls(self):
        directions = ['left', 'right', 'top', 'bottom']
        direction = random.choice(directions)
        ascifight.strategy.issue_order(order="destroy", actor_id=self.actor_id, direction=direction, client=self.client)

    def execute(self, gamestate, rules):
        self.make_attack(gamestate=gamestate)
        #self.destroy_walls()
        self.strategy.execute(gamestate=gamestate, rules=rules)

