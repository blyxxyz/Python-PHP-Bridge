import itertools

from inspect import Parameter, Signature
from typing import Any, Callable, Dict, Iterator, Optional, Set  # noqa: F401

from phpbridge import utils

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


def parse_type_info(bridge: 'PHPBridge', info: Dict[str, Any]) -> Any:
    """Turn a type info dict into an annotation."""
    from phpbridge import objects

    if info['isClass']:
        annotation = objects.get_class(bridge, info['name'])  # type: Any
    else:
        annotation = utils.php_types.get(info['name'], info['name'])
    if info['nullable']:
        annotation = Optional[annotation]

    return annotation


def different_name(name: str) -> Iterator[str]:
    """Look for new names that don't conflict with existing names"""
    yield name
    for n in itertools.count(2):
        yield name + str(n)


def make_signature(bridge: 'PHPBridge', info: Dict[str, Any],
                   add_first: Optional[str] = None):
    """Create a function signature from an info dict."""
    parameters = []
    used_names = set()          # type: Set[str]

    if add_first:
        parameters.append(Parameter(
            name=add_first,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            default=Parameter.empty,
            annotation=Parameter.empty))

    for param in info['params']:
        for param_name in different_name(param['name']):
            if param_name not in used_names:
                used_names.add(param_name)
                break

        default = (param['default'] if param['hasDefault'] else
                   Parameter.empty)

        if param['type'] is None:
            annotation = Parameter.empty
        else:
            annotation = parse_type_info(bridge, param['type'])

        kind = (Parameter.VAR_POSITIONAL if param['variadic'] else
                Parameter.POSITIONAL_OR_KEYWORD)

        parameters.append(Parameter(
            name=param_name,
            kind=kind,
            default=default,
            annotation=annotation))

    return_annotation = (Signature.empty if info['returnType'] is None else
                         parse_type_info(bridge, info['returnType']))

    return Signature(parameters=parameters,
                     return_annotation=return_annotation)


def create_function(bridge: 'PHPBridge', name: str) -> None:
    """Create and register a PHP function."""
    info = bridge.send_command('funcInfo', name)

    if info['name'] in bridge._functions:
        bridge._functions[name] = bridge._functions[info['name']]
        return

    def func(*args) -> Any:
        return bridge.send_command(
            'callFun',
            {'name': name,
             'args': [bridge.encode(arg) for arg in args]})

    func.__doc__ = utils.convert_docblock(info['doc'])
    func.__module__ = '<PHP>'
    func.__name__ = info['name']
    func.__qualname__ = '<PHP>.' + info['name']
    func.__signature__ = make_signature(bridge, info)  # type: ignore
    func._bridge = bridge                              # type: ignore

    bridge._functions[name] = func
    bridge._functions[info['name']] = func


def get_function(bridge: 'PHPBridge', name: str) -> Callable:
    """Get the PHP function that belongs to a certain name."""
    if name not in bridge._functions:
        create_function(bridge, name)
    return bridge._functions[name]
