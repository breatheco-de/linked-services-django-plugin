from .exceptions import ProgrammingError

__init__ = ["set_settings", "get_setting"]

settings = {
    "name": 10,
}


def get_setting(key, default=None):
    res = settings.get(key, default)
    if key == "name" and res is None:
        raise ValueError("Name was not set")

    return res


def set_settings(**kwargs):
    for key, value in kwargs.items():
        if key not in settings:
            raise ProgrammingError(f"Invalid setting {key}")

        settings[key] = value
