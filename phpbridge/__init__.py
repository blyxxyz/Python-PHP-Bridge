import base64
import json
import math
import os
import subprocess as sp
import sys
import types

from typing import Any, Callable, IO, List, Dict  # noqa: F401

from phpbridge import functions, modules, objects

php_server_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'server.php')


class PHPBridge:
    def __init__(self, input_: IO[str], output: IO[str], name: str) -> None:
        self.input = input_
        self.output = output
        self.classes = {}      # type: Dict[str, objects.PHPClass]
        self.objects = {}      # type: Dict[str, objects.PHPObject]
        self.functions = {}     # type: Dict[str, Callable]
        self._debug = False
        self.__name__ = name

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
        result = json.loads(line)
        assert isinstance(result, dict)
        return result

    def encode(self, data: Any) -> dict:
        if isinstance(data, str):
            try:
                data.encode()
                return {'type': 'string', 'value': data}
            except UnicodeEncodeError:
                # string contains surrogates
                data = data.encode(errors='surrogateescape')

        if isinstance(data, bytes):
            return {'type': 'bytes',
                    'value': base64.b64encode(data).decode()}

        if isinstance(data, bool):
            return {'type': 'boolean', 'value': data}

        if isinstance(data, int):
            return {'type': 'integer', 'value': data}

        if isinstance(data, float):
            if math.isnan(data):
                data = 'NAN'
            elif math.isinf(data):
                data = 'INF' if data > 0 else '-INF'
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
                              'hash': data._id}}

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
            elif value == '-INF':
                return -math.inf
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
            cls = self.get_class(value['class'])
            return cls(from_hash=value['hash'])
        elif type_ == 'resource':
            return objects.PHPResource(self, value['type'], value['hash'])
        elif type_ == 'thrownException':
            raise self.decode(value)
        elif type_ == 'bytes':
            # PHP's strings are just byte arrays
            # Decoding this to a bytes object would be problematic
            # It might be meant as a legitimate string, and some binary data
            # could be valid unicode by accident
            value = base64.b64decode(value)
            return value.decode(errors='surrogateescape')
        raise RuntimeError("Unknown type {!r}".format(type_))

    def send_command(self, cmd: str, data: Any = None) -> Any:
        self.send(cmd, data)
        return self.decode(self.receive())

    def resolve(self, path: str, name: str) -> Any:
        if path:
            name = path + '\\' + name
        kind, content = self.send_command('resolveName', name)
        if kind == 'func':
            return self.get_function(content)
        elif kind == 'class':
            return self.get_class(content)
        elif kind == 'const' or kind == 'global':
            return content
        elif kind == 'none':
            raise AttributeError("No construct named '{}' found".format(name))
        else:
            raise RuntimeError("Resolved unknown data type {}".format(kind))

    def get_class(self, name: str) -> objects.PHPClass:
        if name not in self.classes:
            objects.create_class(self, name)
        return self.classes[name]

    def get_function(self, name: str) -> Callable:
        if name not in self.functions:
            functions.create_function(self, name)
        return self.functions[name]


def start_process_unix(fname: str, name: str) -> PHPBridge:
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
    return PHPBridge(os.fdopen(py_in, 'w'), os.fdopen(py_out, 'r'), name)


def start_process_windows(fname: str, name: str) -> PHPBridge:
    """Start a server.php bridge over stdin and stderr."""
    proc = sp.Popen(['php', fname, 'php://stdin', 'php://stderr'],
                    stdin=sp.PIPE, stderr=sp.PIPE,
                    universal_newlines=True)
    return PHPBridge(proc.stdin, proc.stderr, name)


def start_process(fname: str = php_server_path,
                  name: str = 'php') -> PHPBridge:
    """Start server.php and open a bridge to it."""
    if sys.platform.startswith('win32'):
        return start_process_windows(fname, name)
    return start_process_unix(fname, name)


modules.NamespaceFinder(start_process, 'php').register()
