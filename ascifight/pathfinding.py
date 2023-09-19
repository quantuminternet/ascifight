
import httpx
from ascifight.computations import Coordinates, Directions, calc_target_coordinate_direction

max_steps = 100


def find_path(game_state: dict, rules: dict, target: Coordinates,
              team: str, actor_id: int) -> Directions:
    map_size = rules['map_size']
    other_actors = [actor for actor in game_state['actors'] if actor['team'] != team or actor['ident'] != actor_id]
    this_actor = next(actor for actor in game_state['actors'] if actor['team'] == team and actor['ident'] == actor_id)
    origin = Coordinates(x=this_actor['coordinates']['x'], y=this_actor['coordinates']['y'])
    bases = game_state['bases']
    walls = game_state['walls']
    obstacles = {(obj['coordinates']['x'], obj['coordinates']['y']) if 'coordinates' in obj else (obj['x'], obj['y'])
                 for obj_list in (other_actors, bases, walls) for obj in obj_list}

    path_dict = {target: 0}
    current_steps = [target]

    def next_field(field: Coordinates):
        fields = [Coordinates(x=field.x - 1, y=field.y),
                  Coordinates(x=field.x + 1, y=field.y),
                  Coordinates(x=field.x, y=field.y - 1),
                  Coordinates(x=field.x, y=field.y + 1)]
        fields = [f for f in fields if 0 <= f.x < map_size and 0 <= f.y < map_size]
        return fields

    for i in range(0, max_steps):
        next_steps = []
        target_found = False
        for step in current_steps:
            move_count = path_dict[step]
            for field in next_field(step):
                if field in path_dict:
                    continue
                if (field.x, field.y) in obstacles:
                    continue
                path_dict[field] = move_count + 1
                if field.x == origin.x and field.y == origin.y:
                    target_found = True
                    break
                next_steps.append(field)
        if target_found:
            break
        current_steps = next_steps

    origin_next_fields = next_field(origin)
    distance = {field: path_dict.get(field, 500) for field in origin_next_fields}
    distance = dict(sorted(distance.items(), key=lambda item: item[1]))
    next_field = next(iter(distance))
    return calc_target_coordinate_direction(origin, next_field)[0]


if __name__ == '__main__':
    # Ralfs server
    SERVER = "http://84.63.250.234/"
    # local server
    # SERVER = "http://127.0.0.1:8000"
    TEAM = "EverythingsAwesome"


    def get_information(info_type: str):
        url = SERVER + "states/" + info_type
        response = httpx.get(url)
        return response.json()

    game_state = get_information('game_state')
    rules = get_information('game_rules')
    print(rules)

    print(find_path(game_state, rules, Coordinates(x=3, y=12), TEAM, 3))










