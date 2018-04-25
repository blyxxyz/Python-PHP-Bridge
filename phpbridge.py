import json
import math
import os.path
import subprocess as sp
import sys

from typing import Any, IO, List, Union

php_server_path = os.path.join(os.path.dirname(__file__), 'server.php')


class PHPException(Exception):
    pass


class PHPBridge:
    def __init__(self, input_: IO[str], output: IO[str]) -> None:
        self.input = input_
        self.output = output
        self.cls = ClassGetter(self)
        self.const = ConstantGetter(self)
        self.fun = FunctionGetter(self)
        self.globals = GlobalGetter(self)

    def forward_stderr(self) -> None:
        for line in self.output:
            sys.stderr.write(line)
        raise RuntimeError("Can't communicate with PHP")

    def send(self, command: str, data: Any) -> None:
        try:
            json.dump({'cmd': command, 'data': data}, self.input)
            self.input.write('\n')
            self.input.flush()
        except BrokenPipeError:
            self.forward_stderr()

    def receive(self) -> dict:
        line = self.output.readline()
        try:
            return json.loads(line)
        except json.decoder.JSONDecodeError:
            sys.stderr.write(line)
            self.forward_stderr()
            return None

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

        if isinstance(data, dict) and all(type(key) is str for key in data):
            return {'type': 'array', 'value': {k: self.encode(v)
                                               for k, v in data.items()}}
        if isinstance(data, list):
            return {'type': 'array', 'value': [self.encode(item)
                                               for item in data]}

        if isinstance(data, PHPObject) and data._bridge is self:
            return {'type': 'object', 'value': data._hash}

        if isinstance(data, PHPFunction) or isinstance(data, PHPClass):
            # PHP uses strings to represent functions and classes
            # This unfortunately means they will be strings if they come back
            return {'type': 'string', 'value': data.__name__}

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
            return PHPObject(self, value)
        elif type_ == 'thrownException':
            raise PHPException(value['message'])
        raise RuntimeError("Unknown type {!r}".format(type_))

    def send_command(self, cmd: str, data: Any = None) -> Any:
        self.send(cmd, data)
        return self.decode(self.receive())

    def __dir__(self) -> List[str]:
        return (dir(self.cls) + dir(self.const) + dir(self.fun) +
                dir(self.globals))

    def __getattr__(self, attr: str) -> Any:
        kind, content = self.send_command('resolveName', attr)
        if kind == 'func':
            return PHPFunction(self, content)
        elif kind == 'class':
            return PHPClass(self, content)
        elif kind == 'const' or kind == 'global':
            return content
        else:
            raise RuntimeError("Resolved unknown data type {}".format(kind))

    @classmethod
    def start_process(cls, fname: str = php_server_path):
        proc = sp.Popen(['php', fname], stdin=sp.PIPE, stderr=sp.PIPE,
                        universal_newlines=True)
        return cls(proc.stdin, proc.stderr)


class PHPFunction:
    def __init__(self, bridge: PHPBridge, name: str) -> None:
        self._bridge = bridge
        self.__name__ = name

    def __call__(self, *args: Any) -> Any:
        return self._bridge.send_command(
            'callFun',
            {'name': self.__name__,
             'args': [self._bridge.encode(arg) for arg in args]})

    def __repr__(self) -> str:
        return "<PHP function {}>".format(self.__name__)


class PHPObject:
    def __init__(self, bridge: PHPBridge, hash_: Union[str, int]) -> None:
        self._bridge = bridge
        self._hash = hash_

    def __repr__(self) -> str:
        return "<{}>".format(
            self._bridge.send_command(
                'repr', self._bridge.encode(self)).rstrip())

    def __str__(self) -> str:
        try:
            return self._bridge.send_command('str', self._bridge.encode(self))
        except PHPException:
            return repr(self)


class PHPClass:
    def __init__(self, bridge: PHPBridge, name: str) -> None:
        self._bridge = bridge
        self.__name__ = name

    def __call__(self, *args) -> PHPObject:
        return self._bridge.send_command(
            'createObject',
            {'name': self.__name__,
             'args': [self._bridge.encode(arg) for arg in args]})

    def __repr__(self) -> str:
        return "<PHP class '{}'>".format(self.__name__)


class Getter:
    _bridge: PHPBridge

    def __init__(self, bridge: PHPBridge) -> None:
        object.__setattr__(self, '_bridge', bridge)

    def __getattr__(self, attr: str) -> Any:
        raise NotImplementedError

    def __setattr__(self, attr: str, value: Any) -> None:
        raise NotImplementedError

    def __getitem__(self, item: str) -> Any:
        return self.__getattr__(item)

    def __setitem__(self, item: str, value: Any) -> None:
        self.__setattr__(item, value)


class ConstantGetter(Getter):
    def __getattr__(self, attr: str) -> Any:
        return self._bridge.send_command('getConst', attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        return self._bridge.send_command(
            'setConst',
            {'name': attr,
             'value': self._bridge.encode(value)})

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listConsts')


class GlobalGetter(Getter):
    def __getattr__(self, attr: str) -> Any:
        return self._bridge.send_command('getGlobal', attr)

    def __setattr__(self, attr: str, value: Any) -> None:
        return self._bridge.send_command(
            'setGlobal',
            {'name': attr,
             'value': self._bridge.encode(value)})

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listGlobals')


class FunctionGetter(Getter):
    def __getattr__(self, attr: str) -> PHPFunction:
        return PHPFunction(self._bridge, attr)

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listFuns')


class ClassGetter(Getter):
    def __getattr__(self, attr: str) -> PHPClass:
        return PHPClass(self._bridge, attr)

    def __dir__(self) -> List[str]:
        return self._bridge.send_command('listClasses')


php = PHPBridge.start_process()
