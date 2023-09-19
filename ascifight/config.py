import os
import toml


global config
absolute_path = os.path.dirname(__file__)
with open(file=f"{absolute_path}/config.toml", mode="r") as fp:
    config = toml.load(fp)
