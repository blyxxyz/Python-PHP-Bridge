"""PHP classes with special Python behavior.

These classes either provide special methods or inherit from Python classes.
They are not subclassed or instantiated directly. Instead, their methods and
bases are copied to the corresponding PHPClasses. This helps keep the class
hierarchy clean, because each class must be bound to a bridge.
"""

import typing

from typing import Any, Callable, Dict, Optional, Type, Union  # noqa: F401

from phpbridge.objects import PHPObject

predef_classes = {}             # type: Dict[str, Type]

magic_aliases = {
    '__toString': '__str__',
    '__invoke': '__call__'
}                               # type: Dict[str, str]


def predef(_cls: Optional[Type] = None, *,
           name: Optional[str] = None) -> Union[Callable[[Type], Type], Type]:
    """A decorator to add a class to the dictionary of pre-defined classes."""

    def decorator(cls: Type) -> Type:
        nonlocal name
        if name is None:
            name = cls.__name__
        predef_classes[name] = cls
        return cls

    if _cls is None:
        return decorator

    return decorator(_cls)


@predef
class Countable(PHPObject):
    """Classes that can be used with count() (PHP) or len() (Python).

    See also: collections.abc.Sized.
    """
    def __len__(self) -> int:
        return self._bridge.send_command(  # type: ignore
            'count', self._bridge.encode(self))


@predef
class Iterator(PHPObject):
    """Interface for objects that can be iterated.

    See also: collections.abc.Iterator.
    """
    def __next__(self) -> Any:
        status, key, value = self._bridge.send_command(
            'nextIteration', self._bridge.encode(self), decode=True)
        if not status:
            raise StopIteration
        return key, value


@predef
class Traversable(PHPObject):
    """Interface to detect if a class is traversable using a for(each) loop.

    See also: collections.abc.Iterable.
    """
    def __iter__(self) -> typing.Iterator:
        return self._bridge.send_command(  # type: ignore
            'startIteration', self._bridge.encode(self), decode=True)


@predef
class ArrayAccess(PHPObject):
    """Interface to provide accessing objects as arrays.

    Note that the "in" operator only ever checks for valid keys when it comes
    to this class. It's less general than the usual possibilities.
    """
    def __contains__(self, item: Any) -> bool:
        return self._bridge.send_command(  # type: ignore
            'hasItem',
            {'obj': self._bridge.encode(self),
             'offset': self._bridge.encode(item)})

    def __getitem__(self, item: Any) -> Any:
        return self._bridge.send_command(
            'getItem',
            {'obj': self._bridge.encode(self),
             'offset': self._bridge.encode(item)},
            decode=True)

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


@predef
class Throwable(PHPObject, Exception):
    """An exception created in PHP.

    Both a valid Exception and a valid PHPObject, so can be raised and
    caught.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(Exception, self).__init__(self.getMessage())


# Closure is somehow hardwired to be callable, without __invoke
# TODO: It would be nice to generate a signature for this
@predef
class Closure(PHPObject):
    def __call__(self, *args: Any) -> Any:
        return self._bridge.send_command(
            'callObj',
            {'obj': self._bridge.encode(self),
             'args': [self._bridge.encode(arg) for arg in args]},
            decode=True)


@predef(name='ArithmeticError')
class PHPArithmeticError(PHPObject, ArithmeticError):
    pass


@predef(name='AssertionError')
class PHPAssertionError(PHPObject, AssertionError):
    pass


@predef
class OutOfBoundsException(PHPObject, IndexError):
    pass


@predef
class OverflowException(PHPObject, OverflowError):
    pass


@predef
class ParseError(PHPObject, SyntaxError):
    pass


@predef
class RuntimeException(PHPObject, RuntimeError):
    pass


@predef(name='TypeError')
class PHPTypeError(PHPObject, TypeError):
    pass


@predef
class UnexpectedValueException(PHPObject, ValueError):
    pass


@predef(name=r'blyxxyz\PythonServer\Exceptions\AttributeError')
class PHPAttributeError(PHPObject, AttributeError):
    pass
