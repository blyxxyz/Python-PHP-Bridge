Experimental module for calling PHP code from Python.

```python
>>> from phpbridge import php
>>> php.array_flip(["foo", "bar"])
{'foo': 0, 'bar': 1}
>>> php.echo("foo\n")
foo
>>> php.PHP_EOL
'\n'
>>> php.DateTime()
<DateTime Object
(
    [date] => 2018-04-25 16:57:40.059926
    [timezone_type] => 3
    [timezone] => Europe/Berlin
)>
>>> php.get_class_methods(php.DateTime)
['__construct', '__wakeup', '__set_state', 'createFromFormat', 'getLastErrors', 'format', 'modify', 'add', 'sub', 'getTimezone', 'setTimezone', 'getOffset', 'setTime', 'setDate', 'setISODate', 'setTimestamp', 'getTimestamp', 'diff']
>>> php.getimagesize("http://php.net/images/logos/new-php-logo.png")
{'0': 200, '1': 106, '2': 3, '3': 'width="200" height="106"', 'bits': 8, 'mime': 'image/png'}
>>> php.eval("""
... function foo($x)
... {
...     return $x + 1;
... }
... """)
>>> php.foo(3)
4
>>> php.foo()
Traceback (most recent call last):
[...]
phpbridge.PHPException: Too few arguments to function foo(), 0 passed in [...]/python-php-bridge/php/Commands.php on line 39 and exactly 1 expected
>>> php._SERVER['REQUEST_TIME']
1524679655
```

Some current features:
  * Calling functions
  * Getting and setting constants
  * Getting and setting global variables
  * Forwarding exceptions
  * Creating PHP objects and passing them back into PHP
  * Tab completion

Caveats:
  * If any PHP code prints to stderr, the connection is lost (warnings are converted to exceptions to make sure they don't get printed)
  * Returned PHP objects are never garbage collected
  * It's probably pretty slow

Different kinds of things may use the same name, so if there's a constant `foo` and a function `foo`, use `php.fun.foo()` rather than `php.foo()` so it doesn't have to guess. There's
  * `php.cls` for classes
  * `php.const` for constants
  * `php.fun` for functions
  * `php.globals` for globals

This way of accessing PHP constructs also supports indexing, which is currently needed to use namespaces. For example, to create a `\Foo\Bar` object:
```python
>>> php.cls[r'\Foo\Bar']()
<Foo\Bar Object
(
    [biz] => baz
)>
```
(the string is prefixed with an `r` so the backslashes don't need to be escaped)

They also support setting constants and global variables:
```python
>>> php.globals.foo = 'bar'
>>> php.const['baz'] = 'foobar'
>>> php.eval("""
... global $foo;
... return [$foo, baz];
... """)
['bar', 'foobar']
```

The bridge works by piping JSON between the Python process and a PHP process.

There are no dependencies, other than PHP 7.0+ and Python 3.5+. Composer can be used to install development tools and set up autoloading, but it's not required.
