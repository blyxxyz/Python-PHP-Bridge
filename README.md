This is a Python module for running PHP programs. It lets you import PHP functions, classes, objects, constants and variables to work just like regular Python versions.

# Examples

You can call functions:
```
>>> from phpbridge import php
>>> php.array_reverse(['foo', 'bar', 'baz'])
Array.list(['baz', 'bar', 'foo'])
>>> php.echo("foo\n")
foo
>>> php.getimagesize("http://php.net/images/logos/new-php-logo.png")
Array([('0', 200), ('1', 106), ('2', 3), ('3', 'width="200" height="106"'), ('bits', 8), ('mime', 'image/png')])
```

You can create and use objects:
```
>>> php.DateTime
<PHP class 'DateTime'>
>>> date = php.DateTime()
>>> print(date)
<DateTime PHP object (date='2018-05-03 22:59:15.114277', timezone_type=3, timezone='Europe/Berlin')>
>>> date.getOffset()
7200
>>> php.ArrayAccess
<PHP interface 'ArrayAccess'>
>>> issubclass(php.ArrayObject, php.ArrayAccess)
True
```

You can use keyword arguments, even though PHP doesn't support them:
```
>>> date.setDate(year=1900, day=20, month=10)
<DateTime PHP object (date='1900-10-20 22:59:15.114277', timezone_type=3, timezone='Europe/Berlin')>
```

You can loop over iterators and traversables:
```
>>> for path, file in php.RecursiveIteratorIterator(php.RecursiveDirectoryIterator('.git/logs')):
...     print("{}: {}".format(path, file.getSize()))
...
.git/logs/.: 16
.git/logs/..: 144
.git/logs/HEAD: 2461
[...]
```

You can get help:
```
>>> help(php.echo)
Help on function echo:

echo(arg1, *rest)
    Output one or more strings.

    @param mixed $arg1
    @param mixed ...$rest

    @return void
```

You can import namespaces as modules:
```
>>> from phpbridge.php.blyxxyz.PythonServer import NonFunctionProxy
>>> help(NonFunctionProxy)
Help on class blyxxyz\PythonServer\NonFunctionProxy in module phpbridge.php.blyxxyz.PythonServer:

class blyxxyz\PythonServer\NonFunctionProxy(phpbridge.objects.PHPObject)
 |  Provide function-like language constructs as static methods.
 |
 |  `isset` and `empty` are not provided because it's impossible for a real
 |  function to check whether its argument is defined.
 |
 |  Method resolution order:
 |      blyxxyz\PythonServer\NonFunctionProxy
 |      phpbridge.objects.PHPObject
 |      builtins.object
 |
 |  Class methods defined here:
 |
 |  array(val) -> dict from phpbridge.objects.PHPClass
 |      Cast a value to an array.
 |
 |      @param mixed $val
 |
 |      @return array
[...]
```

You can index, and get lengths:
```
>>> arr = php.ArrayObject(['foo', 'bar', 'baz'])
>>> arr[10] = 'foobar'
>>> len(arr)
4
```

You can work with PHP's exceptions:
```
>>> try:
...     php.get_resource_type(3)
... except php.TypeError as e:
...     print(e.getMessage())
...
get_resource_type() expects parameter 1 to be resource, integer given
```

# Features
  * Using PHP functions
    * Keyword arguments are supported and translated based on the signature
    * Docblocks are also converted, so `help` is informative
  * Using PHP classes like Python classes
    * Methods and constants are defined right away based on the PHP class
    * Docblocks are treated like docstrings, so `help` works and is informative
    * The original inheritance structure is copied
    * Default properties become Python properties with documentation
    * Other properties are accessed on the fly as a fallback for attribute access
  * Creating and using objects
  * Importing namespaces as modules
  * Getting and setting constants
  * Getting and setting global variables
  * Translating exceptions so they can be treated as both Python exceptions and PHP objects
  * Tab completion in the interpreter
  * Python-like reprs for PHP objects, with information like var_dump in a more compact form

# Caveats
  * On Windows, stdin and stderr are used to communicate, so PHP can't read input and if it writes to stderr the connection is lost
  * You can only pass basic Python objects into PHP
  * Namespaces can shadow names in an unintuitive way
  * Because PHP only has one kind of array, its arrays are translated to a special kind of ordered dictionary

# Name conflicts
Some PHP packages use the same name both for a class and a namespace. As an example, take `nikic/PHP-Parser`.

`PhpParser\Node` is a class, but `PhpParser\Node\Param` is also a class. This means `phpbridge.php.PhpParser.Node` becomes ambiguous - it could either refer to the `Node` class, or the namespace of the `Param` class.

In case of such a conflict, the class is preferred over the namespace. To get `Param`, a `from` import has to be used:
```
>>> php.require('vendor/autoload.php')
<Composer.Autoload.ClassLoader PHP object (prefixLengthsPsr4=[...: (4)], ...>
>>> import phpbridge.php.PhpParser.Node as Node           # Not the namespace!
>>> Node
<PHP interface 'PhpParser\Node'>
>>> from phpbridge.php.PhpParser.Node import Param        # The class we want
>>> Param
<PHP class 'PhpParser\Node\Param'>
>>> import phpbridge.php.PhpParser.Node.Param as Param    # Doesn't work
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
AttributeError: type object 'PhpParser\Node' has no attribute 'Param'
```

If there are no conflicts, things work as expected:
```
>>> from phpbridge.php.blyxxyz.PythonServer import Commands
>>> Commands
<PHP class 'blyxxyz\PythonServer\Commands'>
>>> import phpbridge.php.blyxxyz.PythonServer as PythonServer
>>> PythonServer
<PHP namespace 'blyxxyz\PythonServer'>
>>> PythonServer.Commands
<PHP class 'blyxxyz\PythonServer\Commands'>
```

# Installing
The only dependencies are PHP 7.0+, Python 3.5+, ext-json and ext-reflection. Composer can be used to install development tools and set up autoloading, but it's not required.
