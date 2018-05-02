"""A module for parsing docblock types into mypy-style types.

This was originally going to be used to enhance the function signatures, but
it's useful to know the types that PHP will actually check for and the docblock
types are visible in the __doc__ anyway so it's not used at all now.

It could still be useful for auto-generating mypy stubs, or something.
"""

from typing import Any, Callable, Dict, Optional, Sequence, Type, Union

import phpbridge
import re


def parse_type(bridge: 'phpbridge.PHPBridge',
               spec: str,
               cls: Optional[Type] = None,
               bases: Optional[Sequence[Type]] = None) -> Any:
    """Try to parse a PHPDoc type specification.

    Mostly follows https://docs.phpdoc.org/guides/types.html.
    """

    if not all(char.isalnum() or char in '|[]?\\'
               for char in spec):
        # The spec is probably too advanced for us to deal with properly
        # In that case, return a string
        # This excludes some valid class names, but if you're using
        # non-alphanumeric unicode in your class names, please stop
        return spec

    simple_types = {
        'string': str,
        'int': int,
        'integer': int,
        'float': float,
        'double': float,        # This is not official but probably better
        'bool': bool,
        'boolean': bool,
        'array': dict,
        'resource': phpbridge.objects.PHPResource,
        'object': phpbridge.objects.PHPObject,
        'null': None,
        'void': None,
        'callable': Callable,
        'mixed': Any,
        'false': False,
        'true': True,
        'self': cls if cls is not None else 'self',
        'static': 'static',     # These are tricky, maybe work them out later
        '$this': '$this'
    }

    parsed = []

    for option in spec.split('|'):  # type: Any

        is_array = False
        if option.endswith('[]'):
            option = option[:-2]
            is_array = True

        is_optional = False
        if option.startswith('?'):
            option = option[1:]
            is_optional = True

        if any(char in option for char in '[]?'):
            # This is too advanced, abort
            return spec

        if option in simple_types:
            option = simple_types[option]
        else:
            try:
                option = bridge.get_class(option)
            except Exception:
                # Give up and keep it as a string
                pass

        if is_array:
            option = Dict[Union[int, str], option]

        if is_optional:
            option = Optional[option]

        parsed.append(option)

    if parsed != [None]:
        # A Union with one member just becomes that member so this is ok
        return Union[tuple(parsed)]
    else:
        # But Union[None] becomes NoneType and that's ugly
        return None


def get_signature(bridge: 'phpbridge.PHPBridge',
                  docblock: str,
                  cls: Optional[Type] = None,
                  bases: Optional[Sequence[Type]] = None):
    params = {name: parse_type(bridge, spec, cls, bases)
              for spec, name in
              re.findall(r'\@param\s+([^\s]*)\s+\$([^\s\*]+)', docblock)}
    match = re.search(r'\@return\s+([^\s]*)', docblock)
    if match is not None:
        ret = parse_type(bridge, match.group(1), cls, bases)
    else:
        # "None" would be a valid return type, so we use this
        ret = ''
    return params, ret
