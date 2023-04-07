import enum
import abc
import random
import itertools

from pydantic import BaseModel, ValidationError, Field
import toml
import structlog

import util

with open("config.toml", mode="r") as fp:
    config = toml.load(fp)


class Team(BaseModel):
    name: str
    password: str
    number: int

    def __eq__(self, another):
        return hasattr(another, "name") and self.name == another.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f"Team {self.name}"


class Directions(str, enum.Enum):
    left = "left"
    right = "right"
    down = "down"
    up = "up"


class Coordinates(BaseModel):
    x: int = Field(
        description="X coordinate is decreased by the 'left' and increased by the 'right' direction.",
        ge=0,
        le=config["game"]["map_size"] - 1,
    )
    y: int = Field(
        description="Y coordinate is decreased by the 'down' and increased by the 'up' direction.",
        ge=0,
        le=config["game"]["map_size"] - 1,
    )

    def __str__(self) -> str:
        return f"({self.x}/{self.y})"

    def __eq__(self, another):
        return (
            hasattr(another, "x")
            and self.x == another.x
            and hasattr(another, "y")
            and self.y == another.y
        )

    def __hash__(self) -> int:
        return hash((self.x, self.y))


class ActorProperty(BaseModel):
    type: str
    grab: float = Field(
        description="The probability to successfully grab or put the flag. "
        "An actor with 0 can not carry the flag. Not even when it is given to it.",
    )
    attack: float = Field(
        description="The probability to successfully attack. An actor with 0 can not attack.",
    )


class BoardObject(BaseModel, abc.ABC):
    pass


class Flag(BoardObject):
    team: Team

    def __eq__(self, another):
        return (
            self.__class__.__name__ == another.__class__.__name__
            and hasattr(another, "team")
            and self.team.name == another.team.name
        )

    def __hash__(self):
        return hash((self.__class__.__name__, self.team.name))


class Actor(BoardObject, abc.ABC):
    ident: int
    team: Team
    grab = 0.0
    attack = 0.0
    flag: Flag | None = None

    def __str__(self):
        return f"Actor ({self.__class__.__name__}) {self.team}-{self.ident}"

    def __eq__(self, another):
        return (
            self.__class__.__name__ == another.__class__.__name__
            and hasattr(another, "ident")
            and self.ident == another.ident
            and hasattr(another, "team")
            and self.team == another.team
        )

    def __hash__(self):
        return hash((self.__class__.__name__, self.ident, self.team))

    @classmethod
    def get_properties(cls) -> ActorProperty:
        return ActorProperty(type=cls.__name__, grab=cls.grab, attack=cls.attack)


class Generalist(Actor):
    grab = 1.0
    attack = 1.0


class Runner(Actor):
    grab = 1.0


class Attacker(Actor):
    attack = 1.0


class Blocker(Actor):
    pass


class Base(BoardObject):
    team: Team

    def __eq__(self, another):
        return (
            self.__class__.__name__ == another.__class__.__name__
            and hasattr(another, "team")
            and self.team.name == another.team.name
        )

    def __hash__(self):
        return hash((self.__class__.__name__, self.team.name))


class Wall(BoardObject):
    pass


class Board:
    def __init__(self, walls=0) -> None:
        self.logger = structlog.get_logger()
        self.map_size = config["game"]["map_size"]
        self.walls = walls

        self.logger = structlog.get_logger()
        self.actors_coordinates: dict[Actor, Coordinates] = {}
        self.flags_coordinates: dict[Flag, Coordinates] = {}
        self.bases_coordinates: dict[Base, Coordinates] = {}
        self.walls_coordinates: set[Coordinates] = set()

    @property
    def base_place_matrix(self):
        return [
            [[1, 4], [1, 4]],
            [[1, 4], [self.map_size - 5, self.map_size - 2]],
            [[self.map_size - 5, self.map_size - 2], [1, 4]],
            [
                [self.map_size - 5, self.map_size - 2],
                [self.map_size - 5, self.map_size - 2],
            ],
        ]

    @property
    def coordinates_actors(self) -> dict[Coordinates, Actor]:
        return {v: k for k, v in self.actors_coordinates.items()}

    @property
    def coordinates_flags(self) -> dict[Coordinates, Flag]:
        # TODO: multiple flags can be in a position! this code does not notice that
        return {v: k for k, v in self.flags_coordinates.items()}

    @property
    def coordinates_bases(self) -> dict[Coordinates, Base]:
        return {v: k for k, v in self.bases_coordinates.items()}

    def get_all_objects(self, coordinates) -> list[BoardObject]:
        base = self.coordinates_bases.get(coordinates)
        actor = self.coordinates_actors.get(coordinates)
        flags = self.coordinates_flags.get(coordinates)
        wall = Wall() if coordinates in self.walls_coordinates else None
        objects = [base, actor, flags, wall]
        return [i for i in objects if i is not None]

    def respawn(self, actor: Actor) -> None:
        base_coordinates = self.bases_coordinates[Base(team=actor.team)]
        possible_spawn_points = []
        for x in range(base_coordinates.x - 2, base_coordinates.x + 3):
            for y in range(base_coordinates.y - 2, base_coordinates.y + 3):
                try:
                    possible_spawn_points.append(Coordinates(x=x, y=y))
                # ignore impossible positions
                except ValidationError:
                    pass
        actor_positions = list(self.actors_coordinates.values())
        flag_positions = list(self.flags_coordinates.values())
        base_positions = list(self.bases_coordinates.values())
        walls_positions = list(self.walls_coordinates)
        forbidden_positions = set(
            flag_positions + actor_positions + base_positions + walls_positions
        )
        self._place_actor_in_area(actor, possible_spawn_points, forbidden_positions)

    def return_flag_to_base(self, flag: Flag) -> None:
        self.flags_coordinates[flag] = self.bases_coordinates[Base(team=flag.team)]

    def place_bases_and_flags(self, teams: list[Team]) -> None:
        available_places = list(range(len(self.base_place_matrix)))
        for team in teams:
            place_chosen = random.choice(available_places)
            available_places.remove(place_chosen)
            x = random.randint(*self.base_place_matrix[place_chosen][0])
            y = random.randint(*self.base_place_matrix[place_chosen][1])
            coordinates = Coordinates(x=x, y=y)
            self.bases_coordinates[Base(team=team)] = coordinates
            self.flags_coordinates[Flag(team=team)] = coordinates

    def place_actors(self, actors: list[Actor], base: Coordinates) -> None:
        starting_places = self._get_area_positions(base, 2)
        starting_places.remove(base)
        random.shuffle(starting_places)
        starting_places = starting_places[: len(actors)]
        for actor, coordinates in zip(actors, starting_places):
            self.actors_coordinates[actor] = coordinates

    def place_walls(self) -> None:
        forbidden_positions = set()
        for base_coordinates in self.bases_coordinates.values():
            forbidden_positions.update(self._get_area_positions(base_coordinates, 3))
        all_combinations = itertools.product(
            *[range(self.map_size), range(self.map_size)]
        )
        all_positions = {Coordinates(x=i[0], y=i[1]) for i in all_combinations}
        possible_coordinates = list(all_positions - forbidden_positions)
        random.shuffle(possible_coordinates)
        self.walls_coordinates = set(possible_coordinates[: self.walls])

    def calc_target_coordinates(
        self, actor: Actor, direction: Directions
    ) -> Coordinates:
        coordinates = self.actors_coordinates[actor]
        new_coordinates = Coordinates(x=coordinates.x, y=coordinates.y)
        if direction == direction.right:
            new_coordinates.x = min(coordinates.x + 1, self.map_size - 1)
        if direction == direction.left:
            new_coordinates.x = max(coordinates.x - 1, 0)
        if direction == direction.up:
            new_coordinates.y = min(coordinates.y + 1, self.map_size - 1)
        if direction == direction.down:
            new_coordinates.y = max(coordinates.y - 1, 0)
        return new_coordinates

    def move(self, actor: Actor, direction: Directions) -> bool:
        new_coordinates = self.calc_target_coordinates(actor, direction)
        return self._try_put_actor(actor, new_coordinates)

    def image(self) -> str:
        field = [["___" for _ in range(self.map_size)] for _ in range(self.map_size)]

        for i, base in enumerate(self.bases_coordinates.values()):
            field[base.y][base.x] = f" {util.colors[i]}\u25D9{util.colors['revert']} "
        for actor, coordinates in self.actors_coordinates.items():
            char = actor.__class__.__name__[0].upper()
            number = actor.ident
            color = util.colors[actor.team.number]
            field[coordinates.y][
                coordinates.x
            ] = f"{color}{char}{number}{util.colors['revert']} "
        for flag, coordinates in self.flags_coordinates.items():
            color = util.colors[flag.team.number]
            before = field[coordinates.y][coordinates.x]
            field[coordinates.y][coordinates.x] = (
                before[:-2] + f" {color}\u25B2{util.colors['revert']}"
            )
        for wall_coordinate in self.walls_coordinates:
            field[wall_coordinate.y][wall_coordinate.x] = "\u2588\u2588\u2588"
        for row in field:
            row.append("\n")
        # reverse so (0,0) is lower left not upper left
        field.reverse()
        joined = "".join(list(itertools.chain.from_iterable(field)))
        return joined

    def _place_actor_in_area(
        self,
        actor: Actor,
        possible_spawn_points: list[Coordinates],
        forbidden_positions: set[Coordinates],
    ) -> None:
        allowed_positions = set(possible_spawn_points) - set(forbidden_positions)
        target_coordinates = random.choice(list(allowed_positions))
        if actor.flag is not None:
            self.logger.info(f"{actor} dropped flag {actor.flag}.")
            actor.flag = None
        self.actors_coordinates[actor] = target_coordinates
        self.logger.info(f"{actor} respawned to coordinates {target_coordinates}.")

    def _get_area_positions(
        self, center: Coordinates, distance: int
    ) -> list[Coordinates]:
        positions: list[Coordinates] = []
        for x in range(center.x - distance, center.x + distance):
            for y in range(center.y - distance, center.y + distance):
                try:
                    positions.append(Coordinates(x=x, y=y))
                    # ignore forbidden space out of bounds
                except ValidationError:
                    pass
        return positions

    def _try_put_actor(self, actor: Actor, new_coordinates: Coordinates) -> bool:
        coordinates = self.actors_coordinates[actor]
        moved = False

        if coordinates == new_coordinates:
            self.logger.warning(f"{actor} did not move. Target field is out of bounds.")
        elif self.coordinates_actors.get(new_coordinates) is not None:
            self.logger.warning(f"{actor} did not move. Target field is occupied.")
        elif self.coordinates_bases.get(new_coordinates) is not None:
            self.logger.warning(f"{actor} did not move. Target field is abase.")
        elif new_coordinates in self.walls_coordinates:
            self.logger.warning(f"{actor} did not move. Target field is a wall.")
        else:
            self.actors_coordinates[actor] = new_coordinates
            moved = True
            # move flag if actor has it
            if actor.flag is not None:
                flag = actor.flag
                self.flags_coordinates[flag] = new_coordinates

            self.logger.info(f"{actor} moved from {coordinates} to {new_coordinates}")

        return moved