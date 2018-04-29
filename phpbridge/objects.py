"""Translation of PHP classes and objects to Python."""

from itertools import product
from typing import Any, Callable, Dict, List, Optional, Type  # noqa: F401
from warnings import warn

from phpbridge.functions import make_signature
from phpbridge import utils

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


class PHPClass(type):
    """The metaclass of all PHP classes and interfaces."""
    _bridge = None              # type: PHPBridge
    _is_abstract = False        # type: bool
    _is_interface = False       # type: bool

    def __call__(self, *a, **kw):
        if self._is_interface:
            raise TypeError("Cannot instantiate interface {}".format(
                self.__qualname__))
        elif self._is_abstract:
            raise TypeError("Cannot instantiate abstract class {}".format(
                self.__qualname__))
        return super().__call__(*a, **kw)

    def __repr__(self):
        if self._is_interface:
            return "<PHP interface '{}'>".format(self.__qualname__)
        elif self._is_abstract:
            return "<PHP abstract class '{}'>".format(self.__qualname__)
        return "<PHP class '{}'>".format(self.__qualname__)


class PHPObject(metaclass=PHPClass):
    """The base class of all instantiatable PHP classes."""
    def __new__(cls, *args, from_hash: Optional[str] = None):
        """Either create or represent a PHP object.

        Args:
            *args: Arguments for the PHP constructor. Must be empty if
                   from_hash is used.
            from_hash: If None: create a new object by sending a createObject
                       command through the bridge. Otherwise: return the
                       representation of an existing remote PHP object with
                       this hash.
        """
        if from_hash is not None:
            assert not args
            if from_hash not in cls._bridge._objects:
                obj = super().__new__(cls)
                object.__setattr__(obj, '_hash', from_hash)
                cls._bridge._objects[obj._hash] = obj
            return cls._bridge._objects[from_hash]
        return cls._bridge.send_command(
            'createObject',
            {'name': cls.__name__,
             'args': [cls._bridge.encode(arg) for arg in args]})

    def __repr__(self) -> str:
        """Represent a PHP object.

        Wrapped in <> because it's a description, not valid Python code.
        """
        return "<{}>".format(
            self._bridge.send_command(
                'repr', self._bridge.encode(self)).rstrip())

    def __str__(self) -> str:
        try:
            return self._bridge.send_command('str', self._bridge.encode(self))
        except Exception:
            return repr(self)

    def __call__(self, *args) -> Any:
        return self._bridge.send_command(
            'callObj',
            {'obj': self._bridge.encode(self),
             'args': [self._bridge.encode(arg) for arg in args]})

    def __getattr__(self, attr: str) -> Any:
        return self._bridge.send_command(
            'getProperty',
            {'obj': self._bridge.encode(self),
             'name': attr})

    def __setattr__(self, attr: str, value: Any) -> None:
        self._bridge.send_command(
            'setProperty',
            {'obj': self._bridge.encode(self),
             'name': attr,
             'value': self._bridge.encode(value)})

    def __dir__(self) -> List[str]:
        return super().__dir__() + self._bridge.send_command(
            'listNonDefaultProperties', self._bridge.encode(self))


def make_method(bridge, classname, name, info):

    def method(*args, **kwargs) -> Any:
        self, *args = utils.parse_args(
            method.__signature__, args, kwargs)  # type: ignore
        return bridge.send_command(
            'callMethod',
            {'obj': bridge.encode(self),
             'name': name,
             'args': [bridge.encode(arg) for arg in args]})

    method.__module__ = '<PHP>'
    method.__name__ = name
    method.__qualname__ = '<PHP>.{}.{}'.format(classname, name)

    if info['doc'] is not False:
        method.__doc__ = utils.convert_docblock(info['doc'])

    if info['static']:
        # mypy doesn't know classmethods are callable
        method = classmethod(method)  # type: ignore

    return method


def create_property(name: str, doc: str) -> property:
    def getter(self):
        return self._bridge.send_command(
            'getProperty', {'obj': self._bridge.encode(self), 'name': name})

    def setter(self, value):
        return self._bridge.send_command(
            'setProperty',
            {'obj': self._bridge.encode(self),
             'name': name,
             'value': self._bridge.encode(value)})

    def deleter(self):
        return self._bridge.send_command(
            'unsetProperty', {'obj': self._bridge.encode(self), 'name': name})

    getter.__doc__ = doc

    return property(getter, setter, deleter)


def create_class(bridge: 'PHPBridge', unresolved_classname: str) -> None:
    """Create and register a PHPClass.

    Args:
        bridge: The bridge the class belongs to.
        unresolved_classname: The name of the class.
    """
    info = bridge.send_command('classInfo', unresolved_classname)

    classname = info['name']            # type: str
    methods = info['methods']           # type: Dict[str, Dict[str, Any]]
    interfaces = info['interfaces']     # type: List[str]
    consts = info['consts']             # type: Dict[str, Any]
    properties = info['properties']     # type: Dict[str, Dict[str, Any]]
    doc = info['doc']                   # type: str
    parent = info['parent']             # type: str
    is_abstract = info['isAbstract']    # type: bool
    is_interface = info['isInterface']  # type: bool

    # "\ArrayObject" resolves to the same class as "ArrayObject", so we want
    # them to be the same Python objects as well
    if classname in bridge._classes:
        bridge._classes[unresolved_classname] = bridge._classes[classname]
        return

    bindings = {}               # type: Dict[str, Any]
    created_methods = {}        # type: Dict[str, Callable]

    if consts:
        # if it's empty it's a list, because of PHP
        for name, value in consts.items():
            bindings[name] = value

    if properties:
        for name, property_info in properties.items():
            if name in bindings:
                warn("'{}' on class '{}' has multiple meanings".format(
                    name, classname))
            property_doc = utils.convert_docblock(property_info['doc'])
            bindings[name] = create_property(name, property_doc)

    if methods:
        for name, method_info in methods.items():
            if name in bindings:
                warn("'{}' on class '{}' has multiple meanings".format(
                    name, classname))
            method = make_method(bridge, classname, name, method_info)
            bindings[name] = method
            created_methods[name] = method

    bases = [PHPObject]         # type: List[Type]
    if parent is not False:
        bases.append(get_class(bridge, parent))

    for interface in interfaces:
        bases.append(get_class(bridge, interface))

    # Bind the magic methods needed to make these interfaces work
    # TODO: figure out something less ugly
    from phpbridge.classes import predef_classes
    if classname in predef_classes:
        predef = predef_classes[classname]
        for name, value in predef.__dict__.items():
            if callable(value):
                bindings[name] = value
        if doc is False:
            doc = predef.__doc__
        bases += predef.__bases__

    # Remove redundant bases
    while True:
        for (ind_a, a), (ind_b, b) in product(enumerate(bases),
                                              enumerate(bases)):
            if ind_a != ind_b and issubclass(a, b):
                # Don't use list.remove because maybe a == b
                # It's cleaner to keep the first occurrence
                del bases[ind_b]
                # Restart the loop because we modified bases
                break
        else:
            break

    # do this one last to make sure it isn't replaced, it's essential
    bindings['_bridge'] = bridge

    cls = PHPClass(classname, tuple(bases), bindings)
    cls._bridge = bridge
    cls._is_abstract = is_abstract
    cls._is_interface = is_interface

    cls.__doc__ = utils.convert_docblock(doc)
    cls.__module__ = '<PHP>'

    bridge._classes[unresolved_classname] = cls
    bridge._classes[classname] = cls

    # Only now do we attach signatures, because the signatures may contain the
    # class we just registered
    if methods:
        for name, method_info in methods.items():
            func = created_methods[name]
            if method_info['static']:
                # classmethod
                func = func.__func__  # type: ignore
            signature = make_signature(bridge, method_info, add_first='self')
            func.__signature__ = signature  # type: ignore


def get_class(bridge: 'PHPBridge', name: str) -> PHPClass:
    """Get the PHPClass that a name resolves to."""
    if name not in bridge._classes:
        create_class(bridge, name)
    return bridge._classes[name]


class PHPResource:
    """A representation of a remote resource value.

    Not technically an object, but similar in a lot of ways. Resources have a
    type (represented by a string) and an identifier used for reference
    counting.
    """
    def __init__(self, bridge, type_, hash_):
        # Leading underscores are not necessary here but nice for consistency
        self._bridge = bridge
        self._type = type_
        self._hash = hash_

    def __repr__(self):
        """Mimics print_r output for resources, but more informative."""
        return "<PHP {} resource id #{}>".format(self._type, self._hash)
