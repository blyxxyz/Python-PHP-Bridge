import json
import subprocess as sp

class PHPBridge:
    def __init__(self, input_, output):
        self.input = input_
        self.output = output
        self.const = ConstantGetter(self)
        self.fun = FunctionGetter(self)
        self.ns = NamespaceBuilder(self)

    def send(self, command):
        json.dump(command, self.input)
        self.input.write('\n')
        self.input.flush()
        ret = self.output.readline()
        ret = json.loads(ret)
        if 'err' in ret:
            raise Exception(ret['err'])
        return ret['ret']

    def send_command(self, cmd, data):
        return self.send({
            'cmd': cmd,
            'data': data
        })

    @classmethod
    def start_process(cls, fname='server.php'):
        proc = sp.Popen(['php', fname], stdin=sp.PIPE, stderr=sp.PIPE,
                        universal_newlines=True)
        return cls(proc.stdin, proc.stderr)


class ConstantGetter:
    def __init__(self, bridge, namespace=None):
        self.bridge = bridge
        self.namespace = namespace

    def __getattr__(self, attr):
        if self.namespace and '\\' not in attr:
            attr = self.namespace + attr
        return self.bridge.send_command('getConst', attr)

    def __getitem__(self, item):
        return self.__getattr__(item)


class FunctionGetter:
    def __init__(self, bridge, namespace=None):
        self.bridge = bridge
        self.namespace = namespace

    def __getattr__(self, attr):
        bridge = self.bridge
        if self.namespace and '\\' not in attr:
            attr = self.namespace + attr
        def func(*args):
            return bridge.send_command(
                'funcall',
                {
                    'func': attr,
                    'args': args
                }
            )
        func.__name__ = attr
        return func

    def __getitem__(self, item):
        return getattr(self, item)


class Namespace:
    def __init__(self, bridge, namespace):
        self.bridge = bridge
        self.namespace = namespace
        self.fun = FunctionGetter(self.bridge, self.namespace)


class NamespaceBuilder:
    def __init__(self, bridge, namespace='\\'):
        self.bridge = bridge
        self.namespace = namespace

    def __getattr__(self, attr):
        if attr == '_':
            return Namespace(self.bridge, self.namespace)
        return self.__class__(self.bridge, self.namespace + attr + '\\')

    def __repr__(self):
        return self.namespace


php = PHPBridge.start_process()
