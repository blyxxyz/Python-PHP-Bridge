import importlib
import sys

from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import (Any, Callable, Dict, Generator,  # noqa: F401
                    List, Optional, Union)
from warnings import warn

import phpbridge

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401

bridges = {}                # type: Dict[PHPBridge, str]


class Namespace(ModuleType):
    def __init__(self, name: str, doc: Optional[str] = None, *,
                 bridge: 'PHPBridge', path: str) -> None:
        super().__init__(name, doc)
        self._bridge = bridge
        self._path = path
        self.__path__ = []      # type: List[str]
        if name.endswith('_'):
            warn("Importing namespace '{}'. Are you sure it ends with an "
                 "underscore?".format(name))

    def __getattr__(self, attr: str) -> Any:
        if attr.endswith('_'):
            attr = attr[:-1]
        return self._bridge.resolve(self._path, attr)

    def __dir__(self) -> Generator:
        dir_ = super().__dir__()
        yield from dir_
        dir_ = set(dir_)
        for entry in self._bridge.send_command('listEverything', self._path):
            if '\\' in entry:
                continue
            if entry in dir_:
                # Provide alias for a name that's shadowed by a namespace.
                # This is not quite correct, but should usually work.
                # The main risk is an accidental import with a trailing
                # underscore.
                entry = entry + '_'
            yield entry

    @property
    def __all__(self) -> List[str]:
        """This is unreliable because of autoloading."""
        return list(dir(self))

    def __repr__(self) -> str:
        if self._path:
            return "<PHP namespace '{}'>".format(self._path)
        return "<PHP global namespace>"

    def __getitem__(self, index: str) -> Any:
        try:
            return self.__getattr__(index)
        except AttributeError as e:
            raise IndexError(*e.args)


class NamespaceLoader(importlib.abc.Loader):
    def __init__(self, bridge: 'PHPBridge', path: str) -> None:
        self.bridge = bridge
        self.path = path

    def create_module(self, spec: ModuleSpec) -> Namespace:
        return Namespace(spec.name, bridge=self.bridge, path=self.path)

    def exec_module(self, module: ModuleType) -> None:
        pass


class NamespaceFinder(importlib.abc.MetaPathFinder):
    """Import PHP namespaces over a bridge."""
    def __init__(self, bridge: Union['PHPBridge', Callable[[], 'PHPBridge']],
                 name: str) -> None:
        self.bridge = bridge
        self.prefix = __package__ + '.' + name
        if isinstance(self.bridge, phpbridge.PHPBridge):
            bridges[self.bridge] = self.prefix

    def resolve(self, name: str) -> Optional[str]:
        """Parse a module name into a namespace identity.

        Args:
            - name: The prospective module path.

        Return:
            - None if the name doesn't specify a namespace.
            - A string representing the namespace otherwise.
        """
        if name == self.prefix:
            return ''

        if not name.startswith(self.prefix + '.'):
            return None

        name = name[len(self.prefix) + 1:]
        return name.replace('.', '\\')

    def find_spec(self, fullname: str, path: Any,
                  target: Optional[ModuleType] = None) -> Optional[ModuleSpec]:
        namespace = self.resolve(fullname)
        if namespace is None:
            return None
        if not isinstance(self.bridge, phpbridge.PHPBridge):
            # Lazy bridge
            self.bridge = self.bridge()
            bridges[self.bridge] = self.prefix
        loader = NamespaceLoader(self.bridge, namespace)
        return ModuleSpec(fullname, loader, is_package=True)

    def register(self) -> None:
        """Add self to sys.meta_path."""
        if self not in sys.meta_path:
            sys.meta_path.append(self)


def get_module(bridge: 'PHPBridge', name: str) -> str:
    """Get the full name of the module that contains a name's namespace."""
    prefix = bridges[bridge]
    namespace, _, name = name.rpartition('\\')
    if namespace == '':
        module = prefix
    else:
        module = prefix + '.' + namespace.replace('\\', '.')
    if module not in sys.modules:
        importlib.import_module(module)
    return module


def basename(fullyqualname: str) -> str:
    """Remove a name's namespace, so it can be used in a __qualname__.

    It may seem wrong that the fully qualified PHP name is used as __name__,
    and the unqualified PHP name is used as __qualname__, but Python's
    qualified names shouldn't include the module name.
    """
    return fullyqualname.rpartition('\\')[2]
