import random

import ascifight.strategy
import ascifight.computations as computations


class Actor:
    def __init__(self, strategy, actor_id: int, client):
        self.actor_id = actor_id
        self.client = client
        self.strategy = strategy

    def make_attack(self):
        directions = ['left', 'right', 'top', 'bottom']
        direction = random.choice(directions)
        ascifight.strategy.issue_order(order="attack", actor_id=self.actor_id, direction=direction, client=self.client)

    def destroy_walls(self):
        directions = ['left', 'right', 'top', 'bottom']
        direction = random.choice(directions)
        ascifight.strategy.issue_order(order="destroy", actor_id=self.actor_id, direction=direction, client=self.client)

    def execute(self, gamestate):
        self.make_attack()
        self.destroy_walls()
        self.strategy.execute(gamestate=gamestate)

