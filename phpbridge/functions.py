import itertools

from inspect import Parameter, Signature
from typing import Any, Callable, Dict, Iterator, Optional, Set  # noqa: F401

from phpbridge import modules, utils

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


def parse_type_info(bridge: 'PHPBridge', info: Dict[str, Any]) -> Any:
    """Turn a type info dict into an annotation."""
    from phpbridge import objects

    if info['isClass']:
        try:
            annotation = bridge.get_class(info['name'])  # type: Any
        except Exception:
            # This probably means the type annotation is invalid.
            # PHP just lets that happen, because the annotation might start
            # existing in the future. So we'll allow it too. But we can't get
            # the class, so use the name of the class instead.
            annotation = (modules.get_module(bridge, info['name']) + '.' +
                          modules.basename(info['name']))
    else:
        annotation = objects.php_types.get(info['name'], info['name'])
    if info['nullable']:
        annotation = Optional[annotation]

    return annotation


def different_name(name: str) -> Iterator[str]:
    """Look for new names that don't conflict with existing names."""
    yield name
    for n in itertools.count(2):
        yield name + str(n)


def make_signature(bridge: 'PHPBridge', info: Dict[str, Any],
                   add_first: Optional[str] = None) -> Signature:
    """Create a function signature from an info dict."""
    parameters = []
    used_names = set()          # type: Set[str]

    if add_first:
        parameters.append(Parameter(
            name=add_first,
            kind=Parameter.POSITIONAL_OR_KEYWORD,
            default=Parameter.empty,
            annotation=Parameter.empty))
        used_names.add(add_first)

    # Mysteriously enough, PHP lets you make a function with default arguments
    # before arguments without a default. Python doesn't. So if that happens,
    # we mark it as an unknown default.
    # default_required is set to True as soon as we find the first parameter
    # with a default value.
    default_required = False

    for param in info['params']:

        for param_name in different_name(param['name']):
            if param_name not in used_names:
                used_names.add(param_name)
                break

        default = (bridge.decode(param['default']) if param['hasDefault'] else
                   Parameter.empty)

        if (param['isOptional'] and not param['variadic'] and
                default is Parameter.empty):
            # Some methods have optional parameters without (visible) default
            # values. We'll use this to represent those.
            default = utils.unknown_param_default

        if (default_required and default is Parameter.empty and
                not param['variadic']):
            default = utils.unknown_param_default

        if default is not Parameter.empty:
            # From now on, we need a default value even if we can't find one.
            default_required = True

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


default_constructor_signature = Signature(
    parameters=[Parameter(name='cls',
                          kind=Parameter.POSITIONAL_OR_KEYWORD,
                          default=Parameter.empty,
                          annotation=Parameter.empty)],
    return_annotation=Signature.empty)


def create_function(bridge: 'PHPBridge', name: str) -> None:
    """Create and register a PHP function."""
    info = bridge.send_command('funcInfo', name)

    if info['name'] in bridge.functions:
        bridge.functions[name] = bridge.functions[info['name']]
        return

    def func(*args: Any, **kwargs: Any) -> Any:
        args = utils.parse_args(
            func.__signature__, args, kwargs)  # type: ignore
        return bridge.send_command(
            'callFun',
            {'name': name,
             'args': [bridge.encode(arg) for arg in args]},
            decode=True)

    func.__doc__ = utils.convert_docblock(info['doc'])
    func.__module__ = modules.get_module(bridge, name)
    func.__name__ = info['name']
    func.__qualname__ = modules.basename(info['name'])
    func.__signature__ = make_signature(bridge, info)  # type: ignore
    func._bridge = bridge                              # type: ignore

    bridge.functions[name] = func
    bridge.functions[info['name']] = func
