from .exceptions import ProgrammingError

__init__ = ["set_settings", "get_setting"]

settings = {
    "app_name": None,
}


def get_setting(key, default=None):
    res = settings.get(key, None)
    if key == "app_name" and res is None:
        raise ValueError("App name was not set")

    if res is None:
        return default

    return res


def set_settings(**kwargs):
    for key, value in kwargs.items():
        if key not in settings:
            raise ProgrammingError(f"Invalid setting {key}")

        settings[key] = value
