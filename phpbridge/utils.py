from inspect import Parameter, Signature
from typing import Any, Dict, List, Mapping, Sequence

php_types = {
    'int': int,
    'integer': int,
    'bool': bool,
    'boolean': bool,
    'array': dict,
    'float': float,
    'double': float,
    'string': str
}


def convert_docblock(doc):
    """Strip the comment syntax out of a docblock."""
    if not isinstance(doc, str):
        return doc
    doc = doc.strip('/*')
    lines = doc.split('\n')
    lines = [line.strip() for line in lines]
    lines = [line[1:] if line.startswith('*') else line
             for line in lines]
    return '\n'.join(lines)


def parse_args(signature: Signature, args: Sequence[Any],
               kwargs: Dict[str, Any]) -> List[Any]:
    """Use a function signature to interpret keyword arguments.

    If no keyword arguments are provided, args is always returned unchanged.
    This ensures that it's possible to call a function even if the signature
    is inaccurate.
    """
    if not kwargs:
        return args
    args = list(args)
    kwargs = dict(kwargs)
    parameters = list(signature.parameters.values())
    while kwargs:
        index = len(args)
        if index >= len(parameters):
            key, value = kwargs.popitem()
            raise TypeError("Can't handle keyword argument '{}'".format(key))
        cur_param = parameters[index]
        name = cur_param.name
        default = cur_param.default
        if name in kwargs:
            args.append(kwargs.pop(name))
        else:
            if default == Parameter.empty:
                raise TypeError("Missing required argument '{}'".format(name))
            args.append(default)
    return args
