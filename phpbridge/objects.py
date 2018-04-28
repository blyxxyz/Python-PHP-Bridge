"""Translation of PHP classes and objects to Python."""

from itertools import product
from typing import Any, Dict, List, Optional, Type  # noqa: F401
from warnings import warn

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
            return "<abstract PHP class '{}'>".format(self.__qualname__)
        return "<PHP class '{}'>".format(self.__qualname__)


class PHPObject(metaclass=PHPClass):
    """The base class of all instantiatable PHP classes."""
    _bridge = None              # type: PHPBridge
    _hash = None                # type: str

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
                object.__setattr__(obj, '_bridge', cls._bridge)
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
        except Throwable:
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
            'listProperties', self._bridge.encode(self))


class Countable(PHPObject):
    """Classes that can be used with count() (PHP) or len() (Python).

    See also: collections.abc.Sized.
    """
    def __len__(self) -> int:
        return self._bridge.send_command('count', self._bridge.encode(self))


class Iterator(PHPObject):
    """Interface for objects that can be iterated.

    See also: collections.abc.Iterator.
    """
    def __next__(self) -> Any:
        status, key, value = self._bridge.send_command(
            'nextIteration', self._bridge.encode(self))
        if not status:
            raise StopIteration
        return key, value


class Traversable(PHPObject):
    """Interface to detect if a class is traversable using a for(each) loop.

    See also: collections.abc.Iterable.
    """
    def __iter__(self) -> Iterator:
        return self._bridge.send_command(
            'startIteration', self._bridge.encode(self))


class ArrayAccess(PHPObject):
    """Interface to provide accessing objects as arrays.

    Note that the "in" operator only ever checks for valid keys when it comes
    to this class. It's less general than the usual possibilities.
    """
    def __contains__(self, item: Any) -> bool:
        return self._bridge.send_command(
            'hasItem',
            {'obj': self._bridge.encode(self),
             'offset': self._bridge.encode(item)})

    def __getitem__(self, item: Any) -> Any:
        return self._bridge.send_command(
            'getItem',
            {'obj': self._bridge.encode(self),
             'offset': self._bridge.encode(item)})

    def __setitem__(self, item: Any, value: Any) -> None:
        self._bridge.send_command(
            'setItem',
            {'obj': self._bridge.encode(self),
             'offset': self._bridge.encode(item),
             'value': self._bridge.encode(value)})

    def __delitem__(self, item: Any) -> None:
        self._bridge.send_command(
            'delItem',
            {'obj': self._bridge.encode(self),
             'offset': self._bridge.encode(item)})


class Throwable(PHPObject, Exception):
    """An exception created in PHP.

    Both a valid Exception and a valid PHPObject, so can be raised and
    caught.
    """
    def __init__(self, *args, from_hash: Optional[str] = None) -> None:
        super(Exception, self).__init__(str(self))


def create_class(bridge: 'PHPBridge', unresolved_classname: str) -> PHPClass:
    """Create and register a PHPClass.

    Args:
        bridge: The bridge the class belongs to.
        unresolved_classname: The name of the class.

    Return:
        A PHPClass, possibly newly created, possibly looked up.
    """
    info = bridge.send_command('classInfo', unresolved_classname)

    classname = info['name']            # type: str
    methods = info['methods']           # type: Dict[str, Dict[str, Any]]
    interfaces = info['interfaces']     # type: List[str]
    consts = info['consts']             # type: Dict[str, Any]
    doc = info['doc']                   # type: str
    parent = info['parent']             # type: str
    is_abstract = info['isAbstract']    # type: bool
    is_interface = info['isInterface']  # type: bool

    # "\ArrayObject" resolves to the same class as "ArrayObject", so we want
    # them to be the same Python objects as well
    if classname in bridge._classes:
        return bridge._classes[classname]

    bindings = {}               # type: Dict[str, Any]

    if consts:
        # if it's empty it's a list, because of PHP
        for name, value in consts.items():
            bindings[name] = value

    if methods:
        for name, method_info in methods.items():
            def method(self: PHPObject, *args, name: str = name) -> Any:
                return bridge.send_command(
                    'callMethod',
                    {'obj': bridge.encode(self),
                     'name': name,
                     'args': [bridge.encode(arg) for arg in args]})

            method.__name__ = name
            if method_info['doc'] is not False:
                method.__doc__ = method_info['doc']

            if method_info['static']:
                # mypy doesn't know classmethods are callable
                method = classmethod(method)  # type: ignore

            if name in bindings:
                warn("const {} on class {} will be shadowed by the method "
                     "with the same name".format(name, classname))
            bindings[name] = method

    bases = [PHPObject]         # type: List[Type]
    if parent is not False:
        bases.append(get_class(bridge, parent))

    for interface in interfaces:
        bases.append(get_class(bridge, interface))

    # Bind the magic methods needed to make these interfaces work
    # TODO: figure out something less ugly
    for predef_interface in [Countable, Iterator, Traversable, ArrayAccess,
                             Throwable]:
        if classname == predef_interface.__name__:
            for name, value in predef_interface.__dict__.items():
                if callable(value):
                    bindings[name] = value
            if doc is False:
                doc = predef_interface.__doc__
            bases += predef_interface.__mro__[1:]

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

    if doc is not False:
        cls.__doc__ = doc

    bridge._classes[classname] = cls

    return cls


def get_class(bridge: 'PHPBridge', name: str) -> PHPClass:
    """Get the PHPClass that a name resolves to."""
    if name not in bridge._classes:
        bridge._classes[name] = create_class(bridge, name)
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
