import os
from os.path import dirname

from benedict import benedict


class Settings:
    def __init__(self, settings_file: str = os.path.join(dirname(dirname(dirname(__file__))), "settings", "settings.json")):
        self.__settings = benedict.from_json(settings_file)

    def get(self, key: str):
        return self.__settings.get(key=key)
