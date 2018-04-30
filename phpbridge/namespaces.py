from typing import Any, List

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


class Namespace:
    def __init__(self, bridge: 'PHPBridge', path: str) -> None:
        self._bridge = bridge
        self._path = path.replace('.', '\\').replace('/', '\\').strip('\\')

    def __getattr__(self, attr: str) -> Any:
        return self._bridge.__getattr__(self._path + '\\' + attr)

    def __dir__(self) -> List[str]:
        leading = '_.' + self._path.replace('\\', '.') + '._.'
        return [entry[len(leading):]
                for entry in dir(self._bridge)
                if entry.startswith(leading)]

    def __repr__(self) -> str:
        return "<PHP namespace '{}'>".format(self._path)


class NamespaceBuilder:
    def __init__(self, bridge: 'PHPBridge', path: str = '') -> None:
        self._bridge = bridge
        self._path = path.replace('.', '\\').replace('/', '\\').strip('\\')
        self._ = Namespace(self._bridge, self._path)

    def __getattr__(self, attr: str) -> Any:
        return self.__class__(self._bridge, self._path + '\\' + attr)

    def __dir__(self) -> List[str]:
        leading = '_.' + self._path.replace('\\', '.')
        if not leading.endswith('.'):
            leading += '.'
        return [entry[len(leading):]
                for entry in dir(self._bridge)
                if entry.startswith(leading)]


def convert_notation(name: str) -> str:
    """Convert an identifier's name to attribute access format."""
    name = name.replace('\\', '.')
    if '.' not in name:
        return name
    name = '_.' + name
    ns, name = name.rsplit('.', 1)
    return ns + '._.' + name
