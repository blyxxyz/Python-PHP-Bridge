"""Translation of PHP classes and objects to Python."""

from itertools import product
from typing import (Any, Callable, Dict, List, Optional, Type,  # noqa: F401
                    Union)
from warnings import warn

from phpbridge.functions import make_signature, default_constructor_signature
from phpbridge import modules, utils

MYPY = False
if MYPY:
    from phpbridge import PHPBridge  # noqa: F401


class PHPClass(type):
    """The metaclass of all PHP classes and interfaces."""
    _bridge = None              # type: PHPBridge
    _name = None                # type: str
    _is_abstract = False
    _is_interface = False
    _is_trait = False

    def __call__(self, *a: Any, **kw: Any) -> Any:
        if self._is_trait:
            raise TypeError("Cannot instantiate trait {}".format(
                self.__name__))
        elif self._is_interface:
            raise TypeError("Cannot instantiate interface {}".format(
                self.__name__))
        elif self._is_abstract:
            raise TypeError("Cannot instantiate abstract class {}".format(
                self.__name__))
        return super().__call__(*a, **kw)

    def __repr__(self) -> str:
        if self._is_trait:
            return "<PHP trait '{}'>".format(self.__name__)
        elif self._is_interface:
            return "<PHP interface '{}'>".format(self.__name__)
        elif self._is_abstract:
            return "<PHP abstract class '{}'>".format(self.__name__)
        return "<PHP class '{}'>".format(self.__name__)


class PHPObject(metaclass=PHPClass):
    """The base class of all instantiatable PHP classes."""
    def __new__(cls, *args: Any) -> Any:
        """Create and return a new object."""
        return cls._bridge.send_command(
            'createObject',
            {'name': cls._name,
             'args': [cls._bridge.encode(arg) for arg in args]},
            decode=True)

    # In theory, this __new__ only shows up if no constructor has been defined,
    # so it doesn't take arguments. In practice we don't want to enforce that,
    # but we'll override the ugly signature.
    __new__.__signature__ = default_constructor_signature  # type: ignore

    def __repr__(self) -> str:
        return self._bridge.send_command(  # type: ignore
            'repr', self._bridge.encode(self), decode=True)

    def __getattr__(self, attr: str) -> Any:
        return self._bridge.send_command(
            'getProperty',
            {'obj': self._bridge.encode(self),
             'name': attr},
            decode=True)

    def __setattr__(self, attr: str, value: Any) -> None:
        self._bridge.send_command(
            'setProperty',
            {'obj': self._bridge.encode(self),
             'name': attr,
             'value': self._bridge.encode(value)})

    def __delattr__(self, attr: str) -> None:
        self._bridge.send_command(
            'unsetProperty',
            {'obj': self._bridge.encode(self),
             'name': attr})

    def __dir__(self) -> List[str]:
        return super().__dir__() + self._bridge.send_command(  # type: ignore
            'listNonDefaultProperties', self._bridge.encode(self))


def make_method(bridge: 'PHPBridge', classname: str, name: str,
                info: dict) -> Callable:

    def method(*args: Any, **kwargs: Any) -> Any:
        self, *args = utils.parse_args(
            method.__signature__, args, kwargs)  # type: ignore
        return bridge.send_command(
            'callMethod',
            {'obj': bridge.encode(self),
             'name': name,
             'args': [bridge.encode(arg) for arg in args]},
            decode=True)

    method.__module__ = modules.get_module(bridge, classname)
    method.__name__ = name
    method.__qualname__ = modules.basename(classname) + '.' + name

    if info['doc'] is not False:
        method.__doc__ = utils.convert_docblock(info['doc'])

    if info['static']:
        # mypy doesn't know classmethods are callable
        return classmethod(method)  # type: ignore

    return method


def create_property(name: str, doc: Optional[str]) -> property:
    def getter(self: PHPObject) -> Any:
        return self._bridge.send_command(
            'getProperty',
            {'obj': self._bridge.encode(self), 'name': name},
            decode=True)

    def setter(self: PHPObject, value: Any) -> None:
        self._bridge.send_command(
            'setProperty',
            {'obj': self._bridge.encode(self),
             'name': name,
             'value': self._bridge.encode(value)})

    def deleter(self: PHPObject) -> None:
        self._bridge.send_command(
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
    traits = info['traits']             # type: List[str]
    consts = info['consts']             # type: Dict[str, Any]
    properties = info['properties']     # type: Dict[str, Dict[str, Any]]
    doc = info['doc']                   # type: Optional[str]
    parent = info['parent']             # type: str
    is_abstract = info['isAbstract']    # type: bool
    is_interface = info['isInterface']  # type: bool
    is_trait = info['isTrait']          # type: bool

    # PHP turns empty associative arrays into empty lists, so
    if not properties:
        properties = {}
    if not consts:
        consts = {}
    if not methods:
        methods = {}

    # "\Foo" resolves to the same class as "Foo", so we want them to be the
    # same Python objects as well
    if classname in bridge.classes:
        bridge.classes[unresolved_classname] = bridge.classes[classname]
        return

    bases = [PHPObject]         # type: List[Type]

    if parent is not False:
        bases.append(bridge.get_class(parent))

    for trait in traits:
        bases.append(bridge.get_class(trait))

    for interface in interfaces:
        bases.append(bridge.get_class(interface))

    bindings = {}               # type: Dict[str, Any]

    for name, value in consts.items():
        bindings[name] = value

    for name, property_info in properties.items():
        if name in bindings:
            warn("'{}' on class '{}' has multiple meanings".format(
                name, classname))
        property_doc = utils.convert_docblock(property_info['doc'])
        bindings[name] = create_property(name, property_doc)

    created_methods = {}        # type: Dict[str, Callable]

    from phpbridge.classes import magic_aliases
    for name, method_info in methods.items():
        if name in bindings:
            warn("'{}' on class '{}' has multiple meanings".format(
                name, classname))
        if method_info['owner'] != classname:
            # Make inheritance visible
            continue

        method = make_method(bridge, classname, name, method_info)

        if (isinstance(method.__doc__, str) and
                '@inheritdoc' in method.__doc__.lower()):
            # If @inheritdoc is used, we manually look for inheritance.
            # If method.__doc__ is empty we leave it empty, and pydoc and
            # inspect know where to look.
            for base in bases:
                try:
                    base_doc = getattr(base, name).__doc__
                    if isinstance(base_doc, str):
                        method.__doc__ = base_doc
                        break
                except AttributeError:
                    pass

        bindings[name] = method
        created_methods[name] = method
        if name in magic_aliases:
            bindings[magic_aliases[name]] = method

        if method_info['isConstructor']:

            def __new__(*args: Any, **kwargs: Any) -> Any:
                cls, *args = utils.parse_args(
                    __new__.__signature__, args, kwargs)  # type: ignore
                return PHPObject.__new__(cls, *args)

            __new__.__module__ = method.__module__
            __new__.__qualname__ = modules.basename(classname) + '.__new__'
            __new__.__doc__ = method.__doc__
            bindings['__new__'] = __new__

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

    # do this last to make sure it isn't replaced
    bindings['_bridge'] = bridge
    bindings['__doc__'] = utils.convert_docblock(doc)
    bindings['__module__'] = modules.get_module(bridge, classname)
    bindings['_is_abstract'] = is_abstract
    bindings['_is_interface'] = is_interface
    bindings['_is_trait'] = is_trait

    # PHP does something really nasty when you make an anonymous class.
    # Each class needs to have a unique name, so it makes a name that goes
    # class@anonymous<null byte><place of definition><hex memory address>
    # The null byte is probably to trick naively written C code into
    # printing only the class@anonymous part.
    # Unfortunately, Python doesn't like those class names, so we'll
    # insert another character that you'll (hopefully) not find in any
    # named class's name because the syntax doesn't allow it.
    typename = classname.replace('\0', '$')
    bindings['_name'] = classname

    cls = PHPClass(typename, tuple(bases), bindings)

    cls.__qualname__ = modules.basename(cls.__name__)

    bridge.classes[unresolved_classname] = cls
    bridge.classes[classname] = cls

    # Only now do we attach signatures, because the signatures may contain the
    # class we just registered
    for name, func in created_methods.items():
        method_info = methods[name]
        if method_info['static']:
            # classmethod
            func = func.__func__  # type: ignore
        signature = make_signature(bridge, method_info, add_first='self')
        func.__signature__ = signature  # type: ignore

        if method_info['isConstructor']:
            cls.__new__.__signature__ = make_signature(  # type: ignore
                bridge, method_info, add_first='cls')


class PHPResource:
    """A representation of a remote resource value.

    Not technically an object, but similar in a lot of ways. Resources have a
    type (represented by a string) and an identifier used for reference
    counting.
    """
    def __init__(self, bridge: 'PHPBridge', type_: str, id_: int) -> None:
        # Leading underscores are not necessary here but nice for consistency
        self._bridge = bridge
        self._type = type_
        self._id = id_

    def __repr__(self) -> str:
        """Mimics print_r output for resources, but more informative."""
        return "<PHP {} resource id #{}>".format(self._type, self._id)


php_types = {
    'int': int,
    'integer': int,
    'bool': bool,
    'boolean': bool,
    'array': dict,
    'float': float,
    'double': float,
    'string': str,
    'void': None,
    'NULL': None,
    'null': None,
    'callable': Callable,
    'true': True,
    'false': False,
    'mixed': Any,
    'object': PHPObject,
    'resource': PHPResource
}
