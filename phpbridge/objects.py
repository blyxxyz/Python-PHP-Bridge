"""Translation of PHP classes and objects to Python."""

from typing import Any, List, Optional, Type  # noqa: F401

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


class PHPClass(type):
    """The metaclass of all PHP classes."""
    _bridge = None              # type: PHPBridge

    def __repr__(self):
        return "<PHP class '{}'>".format(self.__qualname__)


class PHPObject(metaclass=PHPClass):
    """The base class all PHP classes inherit from."""
    _bridge = None              # type: PHPBridge
    _hash = None                # type: str

    def __new__(cls, *args, from_hash: Optional[str] = None,
                super_type: Type = type):
        """Either create or represent a PHP object.

        Args:
            *args: Arguments for the PHP constructor. Must be empty if
                   from_hash is used.
            from_hash: If None: create a new object by sending a createObject
                       command through the bridge. Otherwise: return the
                       representation of an existing remote PHP object with
                       this hash.
            super_type: Which superclass's constructor to call. Important for
                        Throwable, which needs to be constructed as an
                        Exception.
        """
        if from_hash is not None:
            assert not args
            if from_hash not in cls._bridge._objects:
                obj = super(super_type, cls).__new__(cls)
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
    def __new__(cls, *args, from_hash: Optional[str] = None,
                super_type: Type = Exception):
        return super().__new__(cls, *args, from_hash=from_hash,
                               super_type=super_type)

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

    # "\ArrayObject" resolves to the same class as "ArrayObject", so we want
    # them to be the same Python objects as well
    classname = info['name']
    if classname in bridge._classes:
        return bridge._classes[classname]

    bindings = {}

    if info['consts']:
        # if it's empty it's a list, because of PHP
        for name, value in info['consts'].items():
            bindings[name] = value

    if info['methods']:
        for name, method_info in info['methods'].items():
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

            bindings[name] = method

    # do this one last to make sure it isn't replaced, it's essential
    bindings['_bridge'] = bridge

    bases = ([PHPObject] if 'Throwable' not in info['interfaces']
             else [Throwable])  # type: List[Type]
    for interface in Countable, Traversable, Iterator, ArrayAccess:
        if interface.__name__ in info['interfaces']:
            bases.append(interface)

    # If PHPObject is listed first Python can't create a consistent MRO
    base_tuple = tuple(reversed(bases))
    cls = PHPClass(info['name'], base_tuple, bindings)
    cls._bridge = bridge

    if info['doc'] is not False:
        cls.__doc__ = info['doc']

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
