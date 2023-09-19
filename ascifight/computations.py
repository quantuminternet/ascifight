from pydantic import BaseModel, Field
import enum


class Coordinates(BaseModel):
    x: int = Field(
        description="X coordinate is decreased by the 'left' and increased by the"
        " 'right' direction."
    )
    y: int = Field(
        description="Y coordinate is decreased by the 'down' and increased by the"
        " 'up' direction."
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


class Directions(str, enum.Enum):
    left = "left"
    right = "right"
    down = "down"
    up = "up"


def calc_target_coordinates(
    coordinates: Coordinates,
    direction: Directions,
    map_size: int,
) -> Coordinates:
    new_coordinates = Coordinates(x=coordinates.x, y=coordinates.y)
    match direction:
        case direction.right:
            new_coordinates.x = min(coordinates.x + 1, map_size - 1)
        case direction.left:
            new_coordinates.x = max(coordinates.x - 1, 0)
        case direction.up:
            new_coordinates.y = min(coordinates.y + 1, map_size - 1)
        case direction.down:
            new_coordinates.y = max(coordinates.y - 1, 0)
    return new_coordinates


def calc_target_coordinate_direction(
    origin: Coordinates,
    target: Coordinates,
) -> list[Directions]:
    direction = [Directions.up]

    x, y = distance_vector(origin, target)

    if abs(x) == abs(y):
        if x > 0 and y > 0:
            direction = [Directions.up, Directions.right]
        elif x > 0 and y < 0:
            direction = [Directions.right, Directions.down]
        elif x < 0 and y > 0:
            direction = [Directions.left, Directions.up]
        elif x < 0 and y < 0:
            direction = [Directions.down, Directions.left]

    elif abs(y) > abs(x):
        if y > 0:
            direction = [Directions.up]
        else:
            direction = [Directions.down]
    else:
        if x > 0:
            direction = [Directions.right]
        else:
            direction = [Directions.left]

    return direction


def distance(
    origin: Coordinates,
    target: Coordinates,
) -> int:
    x, y = distance_vector(origin, target)
    return abs(x) + abs(y)


def distance_vector(
    origin: Coordinates,
    target: Coordinates,
) -> tuple[int, int]:
    x = target.x - origin.x
    y = target.y - origin.y
    return x, y