from typing import Any

from .argument_parser import argument_parser
from .exceptions import BadArgument

__all__ = ["create_models"]

list_of_args = list[tuple[int, dict[str, Any]]]
args = list[tuple[int, dict[str, Any]]]


def create_models(attr, path, **kwargs):
    result = [
        cycle(how_many).blend(
            path,
            **{
                **kwargs,
                **arguments,
            },
        )
        for how_many, arguments in argument_parser(attr)
    ]

    if len(result) == 1:
        result = result[0]

    return result
