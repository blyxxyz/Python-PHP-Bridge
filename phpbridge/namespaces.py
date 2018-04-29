MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


class Namespace:
    def __init__(self, bridge: 'PHPBridge', path: str):
        self._bridge = bridge
        self._path = path.replace('.', '\\').strip('\\')

    def __getattr__(self, attr):
        return getattr(self._bridge, self._path + '\\' + attr)

    def __dir__(self):
        path = self._path.replace('\\', '.') + '.'
        return [entry[len(path):]
                for entry in dir(self._bridge)
                if entry.startswith(path)]

    def __repr__(self):
        return "<PHP namespace '{}'>".format(self._path)

    def __call__(self, *a, **kw):
        raise TypeError("'{}' is a namespace object. You're probably trying to"
                        " call a non-existent function or class.")
