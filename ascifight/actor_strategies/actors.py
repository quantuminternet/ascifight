import abc

class Strategy(abc.ABC):

    def execute(self, gamestate):
        pass

class Actor:

    def __init__(self, strategy: str):
        self.strategy = self.construct_strategy(strategy=strategy)

    def construct_strategy(self, strategy: str) -> Strategy:
        strategy_dict = {}
        return strategy_dict.get(strategy)

    def make_attack(self):
        pass

    def destroy_walls(self):
        pass


    def execute(self, gamestate):
        self.make_attack()
        self.destroy_walls()
        self.strategy.execute(gamestate=gamestate)

