import base64
import json
import math
import os
import subprocess as sp
import sys
import types

from collections import ChainMap, OrderedDict
from typing import (Any, Callable, IO, Iterator, List, Dict,  # noqa: F401
                    Iterable, Optional, Set, Union)
from weakref import finalize

from phpbridge import functions, modules, objects

php_server_path = os.path.join(
    os.path.dirname(__file__), 'server.php')


class PHPBridge:
    def __init__(self, input_: IO[str], output: IO[str], name: str) -> None:
        self.input = input_
        self.output = output
        self.classes = {}        # type: Dict[str, objects.PHPClass]
        self.functions = {}      # type: Dict[str, Callable]
        self.constants = {}      # type: Dict[str, Any]
        self.cache = ChainMap(self.classes, self.functions, self.constants)
        self._remotes = {}       # type: Dict[Union[int, str], finalize]
        self._collected = set()  # type: Set[Union[int, str]]
        self._debug = False
        self.__name__ = name

    def send(self, command: str, data: Any) -> None:
        if self._debug:
            print(command, data)
        garbage = list(self._collected.copy())
        if self._debug and garbage:
            print("Asking to collect {}".format(garbage))
        json.dump({'cmd': command,
                   'data': data,
                   'garbage': garbage},
                  self.input)
        self.input.write('\n')
        self.input.flush()

    def receive(self) -> Any:
        line = self.output.readline()
        if self._debug:
            print(line, end='')
        if not line:
            # Empty response, not even a newline
            raise RuntimeError("Connection closed")
        response = json.loads(line)
        for key in response['collected']:
            if self._debug:
                print("Confirmed {} collected".format(key))
            if key in self._collected:
                self._collected.remove(key)
            else:
                if self._debug:
                    print("But {} is not pending collection".format(key))
        if response['type'] == 'exception':
            try:
                exception = self.decode(response['data']['value'])
            except Exception as e:
                raise Exception(
                    "Failed decoding exception with message '{}'".format(
                        response['data']['message']))
            raise exception
        elif response['type'] == 'result':
            return response['data']
        else:
            raise Exception("Received response with unknown type {}".format(
                response['type']))

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
                return Array.list(map(self.decode, value))
            elif isinstance(value, dict):
                return Array((key, self.decode(item))
                             for key, item in value.items())
        elif type_ == 'object':
            cls = self.get_class(value['class'])
            return self.get_object(cls, value['hash'])
        elif type_ == 'resource':
            return self.get_resource(value['type'], value['hash'])
        elif type_ == 'bytes':
            # PHP's strings are just byte arrays
            # Decoding this to a bytes object would be problematic
            # It might be meant as a legitimate string, and some binary data
            # could be valid unicode by accident
            value = base64.b64decode(value)
            return value.decode(errors='surrogateescape')
        raise RuntimeError("Unknown type {!r}".format(type_))

    def send_command(self, cmd: str, data: Any = None,
                     decode: bool = False) -> Any:
        self.send(cmd, data)
        result = self.receive()
        if decode:
            result = self.decode(result)
        return result

    def resolve(self, path: str, name: str) -> Any:
        if path:
            name = path + '\\' + name

        if name in self.cache:
            return self.cache[name]
        else:
            kind = self.send_command('resolveName', name)

        if kind == 'class':
            return self.get_class(name)
        elif kind == 'func':
            return self.get_function(name)
        elif kind == 'const':
            return self.get_const(name)
        elif kind == 'global':
            return self.get_global(name)
        elif kind == 'none':
            raise AttributeError("Nothing named '{}' found".format(name))
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

    def get_const(self, name: str) -> Any:
        if name not in self.constants:
            self.constants[name] = self.send_command(
                'getConst', name, decode=True)
        return self.constants[name]

    def get_global(self, name: str) -> Any:
        return self.send_command('getGlobal', name, decode=True)

    def get_object(self, cls: objects.PHPClass,
                   hash_: str) -> objects.PHPObject:
        obj = self._lookup(hash_)
        if obj is not None:
            return obj          # type: ignore
        new_obj = super(objects.PHPObject, cls).__new__(cls)  # type: ignore
        object.__setattr__(new_obj, '_hash', hash_)
        self._register(hash_, new_obj)
        return new_obj          # type: ignore

    def get_resource(self, type_: str, id_: int) -> objects.PHPResource:
        resource = self._lookup(id_)
        if resource is not None:
            return resource     # type: ignore
        new_resource = objects.PHPResource(self, type_, id_)
        self._register(id_, new_resource)
        return new_resource

    def _register(self, ident: Union[int, str],
                  entity: Union[objects.PHPResource,
                                objects.PHPObject]) -> None:
        """Register an object or resource with a weakref."""
        if self._debug:
            print("Registering {}".format(ident))
        self._remotes[ident] = finalize(entity, self._collect, ident)

    def _lookup(self, ident: Union[int, str]) -> Optional[
            Union[objects.PHPResource, objects.PHPObject]]:
        """Look up an existing object for a remote entity."""
        try:
            ref = self._remotes[ident]
        except KeyError:
            return None
        contents = ref.peek()
        if contents is None:
            return None
        return contents[0]

    def _collect(self, ident: Union[int, str]) -> None:
        """Mark an object or resource identifier as garbage collected."""
        if self._debug:
            print("Lost {}".format(ident))
        self._collected.add(ident)
        del self._remotes[ident]


class Array(OrderedDict):
    """An ordered dictionary with some of PHP's idiosyncrasies.

    These can be treated like lists, to some extent. Simple looping yields
    values, not keys. To get keys, explicitly use .keys(). Positive integer
    keys are automatically converted to strings.

    Creating these arrays yourself or modifying them is a bad idea. This class
    only exists to deal with PHP's ambiguities. If not consumed immediately,
    it's best to convert it to a list or a dict, depending on the kind of array
    you expect.
    """
    def __iter__(self) -> Iterator:
        yield from self.values()

    def __getitem__(self, index: Union[int, str, slice]) -> Any:
        if isinstance(index, slice) or isinstance(index, int) and index < 0:
            return list(self.values())[index]
        if isinstance(index, int):
            index = str(index)
        return super().__getitem__(index)

    def __contains__(self, value: Any) -> bool:
        return value in self.values()

    def __setitem__(self, index: Union[int, str], value: Any) -> None:
        if isinstance(index, int):
            index = str(index)
        super().__setitem__(index, value)

    def __delitem__(self, index: Union[int, str]) -> None:
        if isinstance(index, int):
            index = str(index)
        super().__delitem__(index)

    def listable(self) -> bool:
        """Return whether the array could be created from a list."""
        return all(str(ind) == key for ind, key in enumerate(self.keys()))

    @classmethod
    def list(cls, iterable: Iterable) -> 'Array':
        """Create by taking values from a list and using indexes as keys."""
        return cls((str(ind), item)  # type: ignore
                   for ind, item in enumerate(iterable))

    def __repr__(self) -> str:
        if self and self.listable():
            return "{}.list({})".format(self.__class__.__name__,
                                        list(self.values()))
        return super().__repr__()


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
    os.close(php_in)
    os.close(php_out)
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
