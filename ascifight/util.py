import os
import structlog
import toml

import ascifight.computations as computations

absolute_path = os.path.dirname(__file__)
with open(f"{absolute_path}/config.toml", mode="r") as fp:
    config = toml.load(fp)

logger = structlog.get_logger(__name__)


time_stamper = structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S.%f", utc=False)
pre_chain = [
    # Add the log level and a timestamp to the event_dict if the log entry
    # is not from structlog.
    structlog.stdlib.add_log_level,
    # Add extra attributes of LogRecord objects to the event dictionary
    # so that values passed in the extra parameter of log methods pass
    # through to log output.
    structlog.stdlib.ExtraAdder(),
    time_stamper,
]

log_config_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.contextvars.merge_contextvars,
                structlog.processors.JSONRenderer(sort_keys=True),
            ],
            "foreign_pre_chain": pre_chain,
        },
        "colored": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            "foreign_pre_chain": pre_chain,
        },
    },
    "handlers": {
        "default": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "colored",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": f"{config['server']['log_dir']}/game.log",
            "backupCount": 100,
            "formatter": "plain",
        },
    },
    "loggers": {
        "": {
            "handlers": ["default", "file"],
            "level": "DEBUG",
            "propagate": True,
        },
    },
}

flag_icon = "\u25B2"
base_icon = "\u25D9"
wall_icon = "\u2588\u2588\u2588"

colors = {
    0: "\u001b[31m",
    1: "\u001b[32m",
    2: "\u001b[33m",
    3: "\u001b[34m",
    4: "\u001b[35m",
    5: "\u001b[36m",
    "bold": "\033[1m",
    "revert": "\x1b[0m",
}

color_names = {
    0: "red",
    1: "green",
    2: "yellow",
    3: "blue",
    4: "purple",
    5: "cyan",
}

color_rgb_mapping = {
    "white": (255, 255, 255),
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "purple": (128, 0, 128),
    "cyan": (0, 100, 100),
}

api_description = """
**ASCI-Fight** allows you to fight with your teammates in style.

The goal of this game is to score as many points as possible by capturing your 
enemies flags. Go to your enemies bases,  grab the flags and put them on top of 
your own base.Any enemies that try to stop you, you can attack. Of course they will 
respawn, but the won't bother you in the next ticks.

Show your coding prowess by creating the best scripts and dominate your co-workers!

## The Game 

You control a couple of actors with different properties to rule the field of battle.
Depending on their properties they can perform various orders for you. Once the
server is up (which must be the case, because you can read this documentation) there 
is a grace period before the game starts. Once it has started you can give orders for 
a certain time, then all orders are executed at once and the game is waiting for the 
next orders.


The _game_start_ service tells you when the next game is starting.


The game ends after a certain number of points were scored or a certain number of 
ticks have passed.

## Components

Whats in the game you ask? Easy!

### Actors

Actors are your minions you move over the field of battle. They have different 
properties like _grab_ and _attack_. The can perform _orders_ to move, attack and 
grab.

### Bases

Each team has one. Thats where your actor start, where your flag sits and were both 
your actors and your flag return when they are killed or the flag is scored by an 
enemy team.

### Flags

There is a flag in each base. Your actor can grab it, pass it to another actor, 
throw it down or capture it in your own base to score!

### Walls

You, and your actors, cant walk through these!


Find a list of endpoints that allow you to play the game below.






"""
def to_coordinates(input_coords: dict):
    return computations.Coordinates(x=input_coords['x'], y=input_coords['y'])


def compute_direction(origin, target) -> list[computations.Directions]:
    return computations.calc_target_coordinate_direction(to_coordinates(origin), to_coordinates(target))


def compute_distance(origin, target) -> int:
    return computations.distance(to_coordinates(origin), to_coordinates(target))


def get_nearest_enemy_direction(game_state: dict, team: str, actor_id: int) -> list[computations.Directions]:
    enemy_actors = [actor for actor in game_state['actors'] if actor['team'] != team]
    this_actor = next(actor for actor in game_state['actors'] if actor['team'] == team and actor['ident'] == actor_id)
    nearest_enemy = sorted(enemy_actors,
                           key=lambda enemy: computations.distance(to_coordinates(enemy['coordinates']),
                                                                   to_coordinates(this_actor['coordinates'])),
                           reverse=False)[0]
    directions = compute_direction(origin=this_actor['coordinates'], target=nearest_enemy['coordinates'])
    return list(directions)


def get_nearest_enemy_coordinates(game_state: dict, team: str, actor_id: int, actor_type: str | None = None,
                                  enemyteam=None) \
        -> computations.Coordinates:
    enemy_actors = [actor for actor in game_state['actors'] if actor['team'] != team]
    if actor_type:
        enemy_actors = [actor for actor in enemy_actors if actor['type'] == actor_type]

    if enemyteam:
        enemy_actors = [actor for actor in enemy_actors if actor['team'] == enemyteam]

    this_actor = next(actor for actor in game_state['actors'] if actor['team'] == team and actor['ident'] == actor_id)
    nearest_enemy = sorted(enemy_actors,
                           key=lambda enemy: computations.distance(to_coordinates(enemy['coordinates']),
                                                                   to_coordinates(this_actor['coordinates'])),
                           reverse=False)[0]
    return to_coordinates(nearest_enemy['coordinates'])
