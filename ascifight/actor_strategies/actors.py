import abc
import datetime
import random

import ascifight.util


class Actor:
    def __init__(self, strategy, actor_id: int):
        self.actor_id = actor_id
        self.strategy = strategy

    def execute(self, gamestate):
        self.strategy.execute(gamestate=gamestate)

