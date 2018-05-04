"""Stand-alone utility functions."""

from inspect import Parameter, Signature
from typing import Any, Dict, Optional, Tuple


def convert_docblock(doc: Optional[str]) -> Optional[str]:
    """Strip the comment syntax out of a docblock."""
    if not isinstance(doc, str):
        return doc
    doc = doc.strip('/*')
    lines = doc.split('\n')
    lines = [line.strip() for line in lines]
    lines = [line[1:] if line.startswith('*') else line
             for line in lines]
    return '\n'.join(lines)


def parse_args(signature: Signature, orig_args: Tuple,
               orig_kwargs: Dict[str, Any]) -> Tuple:
    """Use a function signature to interpret keyword arguments.

    If no keyword arguments are provided, args is always returned unchanged.
    This ensures that it's possible to call a function even if the signature
    is inaccurate. inspect.Signature.bind is similar, but less forgiving.
    """
    if not orig_kwargs:
        return orig_args
    args = list(orig_args)
    kwargs = dict(orig_kwargs)
    parameters = list(signature.parameters.values())
    while kwargs:
        index = len(args)
        if index >= len(parameters):
            key, value = kwargs.popitem()
            raise TypeError("Can't handle keyword argument '{}'".format(key))
        cur_param = parameters[index]
        name = cur_param.name
        default = cur_param.default
        if default is unknown_param_default:
            raise TypeError("Missing value for argument '{}' with "
                            "unknown default".format(name))
        if name in kwargs:
            args.append(kwargs.pop(name))
        else:
            if default == Parameter.empty:
                raise TypeError("Missing required argument '{}'".format(name))
            args.append(default)
    return tuple(args)


class _UnknownParameterDefaultValue:
    """Represent optional parameters without known defaults."""
    def __repr__(self) -> str:
        return '?'


unknown_param_default = _UnknownParameterDefaultValue()
