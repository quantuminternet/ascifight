from pydantic import BaseModel, Field
from typing import TypeVar
import structlog
from structlog.contextvars import bind_contextvars, unbind_contextvars


import ascifight.config as config
import ascifight.util as util
import ascifight.board.data as data
import ascifight.board.setup as setup
import ascifight.board.actions as actions
import ascifight.board.computations as computations


T = TypeVar("T")


class Order(BaseModel):
    team: str = Field(description="Name of the team to issue the order.")

    def __str__(self) -> str:
        return f"Order by {self.team}."


class AttackOrder(Order):
    actor: int = Field(
        description="The id of the actor, specific to the team.",
        ge=0,
        le=len(config.config["game"]["actors"]) - 1,
    )
    direction: 'computations.Directions' = Field(
        title="Direction",
        description="The direction to attack from the position of the actor.",
    )

    def __str__(self) -> str:
        return f"AttackOrder by Actor {self.team}-{self.actor} -> {self.direction}"


class MoveOrder(Order):
    actor: int = Field(
        description="The id of the actor, specific to the team.",
        ge=0,
        le=len(config.config["game"]["actors"]) - 1,
    )
    direction: 'computations.Directions' = Field(
        title="Direction",
        description=(
            "The direction to move to from the position of the actor. 'up' "
            "increases the y coordinate and 'right' increases the x coordinate."
        ),
    )

    def __str__(self) -> str:
        return f"MoveOrder by Actor {self.team}-{self.actor} -> {self.direction}"


class GrabPutOrder(Order):
    actor: int = Field(
        title="Actor",
        description="The id of the actor, specific to the team.",
        ge=0,
        le=len(config.config["game"]["actors"]) - 1,
    )
    direction: 'computations.Directions' = Field(
        title="Direction",
        description=(
            "The direction to grab of put the flag from the position of the actor. "
        ),
    )

    def __str__(self) -> str:
        return f"GrabPutOrder by Actor {self.team}-{self.actor} -> {self.direction}"


class BuildOrder(Order):
    actor: int = Field(
        description="The id of the actor, specific to the team.",
        ge=0,
        le=len(config.config["game"]["actors"]) - 1,
    )
    direction: 'computations.Directions' = Field(
        title="Direction",
        description="The direction to build from the position of the actor.",
    )

    def __str__(self) -> str:
        return f"BuildOrder by Actor {self.team}-{self.actor} -> {self.direction}"


class DestroyOrder(Order):
    actor: int = Field(
        description="The id of the actor, specific to the team.",
        ge=0,
        le=len(config.config["game"]["actors"]) - 1,
    )
    direction: 'computations.Directions' = Field(
        title="Direction",
        description="The direction to destroy from the position of the actor.",
    )

    def __str__(self) -> str:
        return f"DestroyOrder by Actor {self.team}-{self.actor} -> {self.direction}"


class Game:
    def __init__(
        self,
        game_board: data.BoardData = data.BoardData(),
        score_file=config.config["server"]["scores_file"],
        capture_score: int = config.config["game"]["capture_score"],
        kill_score: int = config.config["game"]["kill_score"],
        winning_bonus: int = config.config["game"]["winning_bonus"],
        max_ticks: int = config.config["game"]["max_ticks"],
        max_score: int = config.config["game"]["max_score"],
    ) -> None:
        self.logger = structlog.get_logger()
        self.score_file: str = score_file
        self.capture_score: int = capture_score
        self.kill_score: int = kill_score
        self.winning_bonus: int = winning_bonus

        self.board = game_board
        self.board_actions = actions.BoardActions(self.board)
        self.scores: dict[data.Team, int] = {}
        self.overall_scores: dict[data.Team, int] = {}
        self.tick = 0
        self.max_ticks: int = max_ticks
        self.max_score: int = max_score

    def initiate_game(self) -> None:
        game_board_setup = setup.BoardSetup(
            game_board_data=self.board,
            teams=config.config["teams"],
            actors=config.config["game"]["actors"],
            map_size=config.config["game"]["map_size"],
            walls=config.config["game"]["walls"],
        )
        game_board_setup.initialize_map()
        self._set_scores()
        self._read_scores()

    def end_game(self) -> None:
        self._write_scores()
        self.logger.info("Game ended.")

    def execute_game_step(self, orders: list[Order]) -> None:
        self.tick += 1

        move_orders: list[MoveOrder] = []
        attack_orders: list[AttackOrder] = []
        grabput_orders: list[GrabPutOrder] = []
        destroy_orders: list[DestroyOrder] = []
        build_orders: list[BuildOrder] = []

        for order in orders:
            if isinstance(order, MoveOrder):
                move_orders.append(order)
            elif isinstance(order, AttackOrder):
                attack_orders.append(order)
            elif isinstance(order, GrabPutOrder):
                grabput_orders.append(order)
            elif isinstance(order, DestroyOrder):
                destroy_orders.append(order)
            elif isinstance(order, BuildOrder):
                build_orders.append(order)

        self.logger.info("Executing move orders.")
        self._execute_move_orders(move_orders)

        self.logger.info("Executing grab/put orders.")
        self._execute_grabput_orders(grabput_orders)

        self.logger.info("Executing attack orders.")
        self._execute_attack_orders(attack_orders)

        self.logger.info("Executing destroy orders.")
        self._execute_destroy_orders(destroy_orders)

        self.logger.info("Executing build orders.")
        self._execute_build_orders(build_orders)

    def scoreboard(self) -> str:
        current_score = " - ".join(
            [
                f"{util.colors[team.number]}{team.name}: {score}{util.colors['revert']}"
                for team, score in self.scores.items()
            ]
        )
        overall_score = " - ".join(
            [
                f"{util.colors[team.number]}{team.name}: {score}{util.colors['revert']}"
                for team, score in self.overall_scores.items()
            ]
        )
        return (
            f"{util.colors['bold']}Overall Score{util.colors['revert']}: "
            f"{overall_score}\n"
            f"{util.colors['bold']}Current Score{util.colors['revert']}: "
            f"{current_score}"
        )

    def _set_scores(self) -> None:
        for team in self.board.names_teams.values():
            self.scores[team] = 0
            self.overall_scores[team] = 0

    def _write_scores(self):
        game_scores = []
        scores = sorted(self.scores.items(), key=lambda x: x[1], reverse=True)

        # if leading teams are tied, nobody gets the winning bonus
        if list(scores)[0][1] == scores[1][1]:
            game_scores = [(team, score) for team, score in scores]
        else:
            # leading team gets the winning bonus
            game_scores = [(scores[0][0], scores[0][1] + self.winning_bonus)]
            game_scores.extend([(team, score) for team, score in scores[1:]])

        with open(self.score_file, "a") as score_file:
            for score in game_scores:
                score_file.write(f"{score[0].name}: {score[1]}\n")

    def _read_scores(self):
        try:
            with open(self.score_file, "r") as score_file:
                for line in score_file:
                    team, score = line.split(":")
                    score = int(score)
                    team = team.strip()
                    try:
                        self.overall_scores[self.board.names_teams[team]] += score
                    # ignore score if team is not in current teams
                    except ValueError:
                        pass
        # if the file is not yet there assume default scores
        except FileNotFoundError:
            pass

    def _actor_dict(self, value: T) -> dict[data.Actor, T]:
        value_dict = {}
        for actor in self.board.teams_actors.values():
            value_dict[actor] = value
        return value_dict

    def _execute_move_orders(self, move_orders: list[MoveOrder]) -> None:
        already_moved = self._actor_dict(False)
        for order in move_orders:
            bind_contextvars(team=order.team)
            self.logger.info(f"Executing {order}")
            actor = self.board.teams_actors[
                (self.board.names_teams[order.team], order.actor)
            ]
            direction = order.direction
            if already_moved[actor]:
                self.logger.warning(f"{actor} already moved this tick.")
            else:
                # if the actor can move
                already_moved[actor], team_that_captured = self.board_actions.move(
                    actor, direction
                )
                if team_that_captured:
                    self.scores[team_that_captured] += self.capture_score

        unbind_contextvars("team")

    def _execute_attack_orders(self, attack_orders: list[AttackOrder]) -> None:
        already_attacked = self._actor_dict(False)
        for order in attack_orders:
            bind_contextvars(team=order.team)
            self.logger.info(f"Executing {order}")
            actor = self.board.teams_actors[
                (self.board.names_teams[order.team], order.actor)
            ]

            if already_attacked[actor]:
                self.logger.warning(f"{actor} already attacked this tick.")
            else:
                already_attacked[actor], team_that_killed = self.board_actions.attack(
                    actor, order.direction
                )
                if team_that_killed:
                    self.scores[team_that_killed] += self.kill_score

        unbind_contextvars("team")

    def _execute_grabput_orders(self, grabput_orders: list[GrabPutOrder]):
        already_grabbed = self._actor_dict(False)
        for order in grabput_orders:
            bind_contextvars(team=order.team)
            self.logger.info(f"Executing {order}")
            actor = self.board.teams_actors[
                (self.board.names_teams[order.team], order.actor)
            ]
            if not already_grabbed[actor]:
                (
                    already_grabbed[actor],
                    team_that_captured,
                ) = self.board_actions.grabput_flag(actor, order.direction)
                if team_that_captured:
                    self.scores[team_that_captured] += self.capture_score
            else:
                self.logger.warning(f"{actor} already grabbed this tick.")
        unbind_contextvars("team")

    def _execute_destroy_orders(self, destroy_orders: list[DestroyOrder]) -> None:
        already_destroyed = self._actor_dict(False)
        for order in destroy_orders:
            bind_contextvars(team=order.team)
            self.logger.info(f"Executing {order}")
            actor = self.board.teams_actors[
                (self.board.names_teams[order.team], order.actor)
            ]

            if already_destroyed[actor]:
                self.logger.warning(f"{actor} already destroyed this tick.")
            else:
                already_destroyed[actor] = self.board_actions.destroy(
                    actor, order.direction
                )

        unbind_contextvars("team")

    def _execute_build_orders(self, build_orders: list[BuildOrder]) -> None:
        already_built = self._actor_dict(False)
        for order in build_orders:
            bind_contextvars(team=order.team)
            self.logger.info(f"Executing {order}")
            actor = self.board.teams_actors[
                (self.board.names_teams[order.team], order.actor)
            ]

            if already_built[actor]:
                self.logger.warning(f"{actor} already built this tick.")
            else:
                already_built[actor] = self.board_actions.build(actor, order.direction)

        unbind_contextvars("team")

    def check_game_end(self):
        return (
            self.tick == self.max_ticks or max(self.scores.values()) == self.max_score
        )
