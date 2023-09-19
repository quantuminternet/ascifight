
import httpx
from ascifight.computations import Coordinates, Directions, calc_target_coordinate_direction

# maximum number of steps allowed. This is to prevent an infinite loop, if the target cannot be reached
MAX_STEPS = 100


def find_path(game_state: dict, rules: dict, target: Coordinates,
              team: str, actor_id: int) -> Directions:
    """
    Find the direction of the shortest path for actor to target coordinates.

    This uses Dijkstra's algorithm. Given a static problem, it will find the shortest path to the target if it exists
    and can be reached with in MAX_STEPS steps.

    :param game_state: game state, as returned by the get_information("game_state") function
    :param rules: game rules, as returned by the get_information("game_rules") function
    :param target: the coordinates where the actor wants to get to
    :param team: the team of our actor
    :param actor_id: the id of our actor
    :returns: the direction of the first step
    TODO: the algorithm also computes the distance, we might want to return it as well

    Known limitations:
    - This might not be the most efficient algorithm (the A* algorithm might perform better)
    - It considers all other actors as obstacles. This may or may not be what you want (an actor with attack capability
      might not care about enemy actors on the path)
      TODO: maybe make it configurable what is should be considered an obstacle and what is not?
    - It might avoid another actor too early, i.e. make an step to the side, although the other actor is still 5 tiles
      away and might move until our actor gets there.
    - Another actor moving might significantly alter the shortest path. In the extreme case, the actor might toggle
      between two paths in subsequent rounds of another actor is blocking and unblocking the shortest path

      Compare:

      A------
      E     |
       █████|
            |
      T<-----

      A
      |E
      |█████
      |
      T
    """

    # we need the rules to determine the boundaries
    map_size = rules['map_size']
    # get all obstacles from the game state
    other_actors = [actor for actor in game_state['actors'] if actor['team'] != team or actor['ident'] != actor_id]
    this_actor = next(actor for actor in game_state['actors'] if actor['team'] == team and actor['ident'] == actor_id)
    origin = Coordinates(x=this_actor['coordinates']['x'], y=this_actor['coordinates']['y'])
    bases = game_state['bases']
    walls = game_state['walls']
    # in the current implementation, walls don't have a "coordinates" field, but just "x" and "y" fields. Hence the
    # need for these two cases
    obstacles = {(obj['coordinates']['x'], obj['coordinates']['y']) if 'coordinates' in obj else (obj['x'], obj['y'])
                 for obj_list in (other_actors, bases, walls) for obj in obj_list}

    # we start from the target, so everything is in "distance from the target". We could do it the other way around,
    # but then we would need to retrace the path at the end
    path_dict = {target: 0}
    current_steps = [target]

    def next_field(field: Coordinates):
        # get all possible fields that are connected to field
        fields = [Coordinates(x=field.x - 1, y=field.y),
                  Coordinates(x=field.x + 1, y=field.y),
                  Coordinates(x=field.x, y=field.y - 1),
                  Coordinates(x=field.x, y=field.y + 1)]
        fields = [f for f in fields if 0 <= f.x < map_size and 0 <= f.y < map_size]
        return fields

    # if we ever reach MAX_STEPS, the algorithm has failed
    for i in range(0, MAX_STEPS):
        next_steps = []
        target_found = False
        for step in current_steps:
            # get the distance value we are at right now
            move_count = path_dict[step]
            for field in next_field(step):
                if field in path_dict:
                    # If we already were at this place, we do not want to check it again (and we definitely are on a
                    # longer path if we already have reached this in fewer steps)
                    continue
                if (field.x, field.y) in obstacles:
                    # If we reach an obstacle, this is a deead end
                    continue
                # If we wanted to, we could use larger values than 1 in some cases (walls that need to be broken down?)
                path_dict[field] = move_count + 1
                if field.x == origin.x and field.y == origin.y:
                    # if we have reached the start, we have the shortest path. We can stop searching
                    target_found = True
                    break
                # if this is a valid path, we will continue going down that path in the next iteration
                next_steps.append(field)
        if target_found:
            break
        current_steps = next_steps

    # we now have an (incomplete) map field -> distance to target. However, if the algorithm did not exceed max steps,
    # there must be a path from origin to target and one of the adjacencies of origin must have a defined value.
    # we extract the one with the minimum value, this is our next step
    # TODO: do we want to tell the user if no path was found? Currently it would just select something at random
    origin_next_fields = next_field(origin)
    distance = {field: path_dict.get(field, 500) for field in origin_next_fields}
    distance = dict(sorted(distance.items(), key=lambda item: item[1]))
    next_field = next(iter(distance))
    return calc_target_coordinate_direction(origin, next_field)[0]











