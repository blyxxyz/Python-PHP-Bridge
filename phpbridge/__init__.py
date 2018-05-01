import json
import math
import os
import subprocess as sp
import sys
import types

from typing import Any, Callable, IO, List, Dict  # noqa: F401

from phpbridge import functions, namespaces, objects

php_server_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'server.php')


class PHPBridge:
    def __init__(self, input_: IO[str], output: IO[str]) -> None:
        self.input = input_
        self.output = output
        self.cls = ClassGetter(self)
        self.const = ConstantGetter(self)
        self.fun = FunctionGetter(self)
        self.globals = GlobalGetter(self)
        self._classes = {}      # type: Dict[str, objects.PHPClass]
        self._objects = {}      # type: Dict[str, objects.PHPObject]
        self._functions = {}    # type: Dict[str, Callable]
        self._ = namespaces.NamespaceBuilder(self, '')
        self._debug = False

    def send(self, command: str, data: Any) -> None:
        if self._debug:
            print(command, data)
        json.dump({'cmd': command, 'data': data}, self.input)
        self.input.write('\n')
        self.input.flush()

    def receive(self) -> dict:
        line = self.output.readline()
        if self._debug:
            print(line)
        return json.loads(line)

    def encode(self, data: Any) -> dict:
        if isinstance(data, str):
            return {'type': 'string', 'value': data}
        if isinstance(data, bool):
            return {'type': 'boolean', 'value': data}
        if isinstance(data, int):
            return {'type': 'integer', 'value': data}
        if isinstance(data, float):
            if math.isnan(data):
                data = 'NAN'
            elif math.isinf(data):
                data = 'INF'
            return {'type': 'double', 'value': data}
        if data is None:
            return {'type': 'NULL', 'value': data}

        if isinstance(data, dict) and all(
                isinstance(key, str) or isinstance(key, int)
                for key in data):
            return {'type': 'array', 'value': {k: self.encode(v)
                                               for k, v in data.items()}}
        if isinstance(data, list):
            return {'type': 'array', 'value': [self.encode(item)
                                               for item in data]}

        if isinstance(data, objects.PHPObject) and data._bridge is self:
            return {'type': 'object',
                    'value': {'class': data.__class__._name,  # type: ignore
                              'hash': data._hash}}

        if isinstance(data, objects.PHPResource) and data._bridge is self:
            return {'type': 'resource',
                    'value': {'type': data._type,
                              'hash': data._hash}}

        if isinstance(data, objects.PHPClass) and data._bridge is self:
            # PHP uses strings to represent functions and classes
            # This unfortunately means they will be strings if they come back
            return {'type': 'string', 'value': data._name}

        if (isinstance(data, types.FunctionType) and
                getattr(data, '_bridge', None) is self):
            return {'type': 'string', 'value': data.__name__}

        if (isinstance(data, types.MethodType) and
                getattr(data.__self__, '_bridge', None) is self):
            return self.encode([data.__self__, data.__name__])

        raise RuntimeError("Can't encode {!r}".format(data))

    def decode(self, data: dict) -> Any:
        type_ = data['type']
        value = data['value']
        if type_ in {'string', 'integer', 'NULL', 'boolean'}:
            return value
        elif type_ == 'double':
            if value == 'INF':
                return math.inf
            elif value == 'NAN':
                return math.nan
            return value
        elif type_ == 'array':
            if isinstance(value, list):
                return [self.decode(item) for item in value]
            elif isinstance(value, dict):
                return {key: self.decode(value)
                        for key, value in value.items()}
        elif type_ == 'object':
            cls = objects.get_class(self, value['class'])
            return cls(from_hash=value['hash'])
        elif type_ == 'resource':
            return objects.PHPResource(self, value['type'], value['hash'])
        elif type_ == 'thrownException':
            raise self.decode(value)
        raise RuntimeError("Unknown type {!r}".format(type_))

    def send_command(self, cmd: str, data: Any = None) -> Any:
        self.send(cmd, data)
        return self.decode(self.receive())

    def __dir__(self) -> List[str]:
        return [namespaces.convert_notation(entry) for entry in
                dir(self.cls) + dir(self.const) + dir(self.fun) +
                dir(self.globals)]

    def __getattr__(self, attr: str) -> Any:
        attr = attr.replace('.', '\\')
        kind, content = self.send_command('resolveName', attr)
        if kind == 'func':
            return functions.get_function(self, content)
        elif kind == 'class':
            return objects.get_class(self, content)
        elif kind == 'const' or kind == 'global':
            return content
        elif kind == 'none':
            raise AttributeError("No construct named '{}' found".format(attr))
        else:
            raise RuntimeError("Resolved unknown data type {}".format(kind))

    def __getitem__(self, item: str) -> Any:
        try:
            return self.__getattr__(item)
        except AttributeError as e:
            raise IndexError(*e.args)


class Getter:
    _bridge = None              # type: PHPBridge

    def __init__(self, bridge: PHPBridge) -> None:
        object.__setattr__(self, '_bridge', bridge)

    def __getattr__(self, attr: str) -> Any:
        raise NotImplementedError

    def __setattr__(self, attr: str, value: Any) -> None:
        raise NotImplementedError

    def __getitem__(self, item: str) -> Any:
        try:
            return self.__getattr__(item)
        except AttributeError as e:
            raise IndexError(*e.args)

    def __setitem__(self, item: str, value: Any) -> None:
        try:
            self.__setattr__(item, value)
        except AttributeError as e:
            raise IndexError(*e.args)


class ConstantGetter(Getter):
    def __getattr__(self, attr: str) -> Any:
        try:
            return self._bridge.send_command('getConst', attr)
        except Exception:
            raise AttributeError("Constant '{}' does not exist".format(attr))

    def __setattr__(self, attr: str, value: Any) -> None:
        try:
            return self._bridge.send_command(
                'setConst',
                {'name': attr,
                 'value': self._bridge.encode(value)})
        except Exception as e:
            raise AttributeError(*e.args)

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listConsts')


class GlobalGetter(Getter):
    def __getattr__(self, attr: str) -> Any:
        try:
            return self._bridge.send_command('getGlobal', attr)
        except Exception:
            raise AttributeError(
                "Global variable '{}' does not exist".format(attr))

    def __setattr__(self, attr: str, value: Any) -> None:
        try:
            return self._bridge.send_command(
                'setGlobal',
                {'name': attr,
                 'value': self._bridge.encode(value)})
        except Exception as e:
            raise AttributeError(*e.args)

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listGlobals')


class FunctionGetter(Getter):
    def __getattr__(self, attr: str) -> Callable:
        return functions.get_function(self._bridge, attr)

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listFuns')


class ClassGetter(Getter):
    def __getattr__(self, attr: str) -> objects.PHPClass:
        return objects.get_class(self._bridge, attr)

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listClasses')


def start_process_unix(fname: str) -> PHPBridge:
    """Start a server.php bridge using two pipes.

    pass_fds is not supported on Windows. It may be that some other way to
    inherit file descriptors exists on Windows. In that case, the Windows
    function should be adjusted, or merged with this one.
    """
    php_in, py_in = os.pipe()
    py_out, php_out = os.pipe()
    sp.Popen(['php', fname, 'php://fd/{}'.format(php_in),
              'php://fd/{}'.format(php_out)],
             pass_fds=[0, 1, 2, php_in, php_out])
    return PHPBridge(os.fdopen(py_in, 'w'), os.fdopen(py_out, 'r'))


def start_process_windows(fname: str) -> PHPBridge:
    """Start a server.php bridge over stdin and stderr."""
    proc = sp.Popen(['php', fname, 'php://stdin', 'php://stderr'],
                    stdin=sp.PIPE, stderr=sp.PIPE,
                    universal_newlines=True)
    return PHPBridge(proc.stdin, proc.stderr)


def start_process(fname: str = php_server_path) -> PHPBridge:
    """Start server.php and open a bridge to it."""
    if sys.platform.startswith('win32'):
        return start_process_windows(fname)
    return start_process_unix(fname)
