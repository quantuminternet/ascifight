import asyncio
import importlib
import datetime
import os
import logging, logging.handlers

import structlog
from structlog.contextvars import bind_contextvars

import ascifight.config as config
import ascifight.globals as globals
import ascifight.game as game

root_logger = logging.getLogger()
logger = structlog.get_logger()
SENTINEL = object()


async def routine():
    while True:
        await single_game()


async def single_game() -> None:
    importlib.reload(config)
    importlib.reload(game)

    pre_game_wait = config.config["server"]["pre_game_wait"]
    for handler in root_logger.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            handler.doRollover()
    my_game = game.Game()

    logger.info("Initiating game.")
    my_game.initiate_game()

    logger.info("Starting pre-game.")
    while pre_game_wait > 0:
        await asyncio.sleep(1)
        pre_game_wait -= 1

    while not my_game.check_game_end():
        await globals.command_queue.put(SENTINEL)

        commands = await get_all_queue_items(globals.command_queue)

        bind_contextvars(tick=my_game.tick)
        os.system("cls" if os.name == "nt" else "clear")

        print(my_game.scoreboard())
        print(my_game.board.image())

        logger.info("Starting tick execution.")
        my_game.execute_game_step(commands)

        logger.info("Waiting for game commands.")
        time_of_next_execution = datetime.datetime.now() + datetime.timedelta(
            0, config.config["server"]["tick_wait_time"]
        )
        logger.info(f"Time of next execution: {time_of_next_execution}")

        await asyncio.sleep(config.config["server"]["tick_wait_time"])
    my_game.end_game()
    os.system("cls" if os.name == "nt" else "clear")
    print(my_game.scoreboard())
    print(my_game.board.image())


async def get_all_queue_items(
    queue: asyncio.Queue[game.Order | object],
) -> list[game.Order]:
    items: list[game.Order] = []
    item = await queue.get()
    while item is not SENTINEL:
        items.append(item)  # type: ignore
        queue.task_done()
        item = await queue.get()
    queue.task_done()
    return items


async def ai_generator():
    import board_computations

    await asyncio.sleep(1)
    while True:
        await asyncio.sleep(5)
        await globals.command_queue.put(
            game.MoveOrder(
                team="Team 1",
                actor=0,
                direction=board_computations.Directions.down,
            )
        )
        await asyncio.sleep(5)
        await globals.command_queue.put(
            game.MoveOrder(
                team="Team 2",
                actor=0,
                direction=board_computations.Directions.right,
            )
        )
