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
```

Some current features:
  * Calling functions
  * Accessing constants
  * Forwarding exceptions
  * Creating PHP objects and passing them back into PHP
  * Tab completion

Caveats:
  * If any PHP code prints to stderr, the connection is lost (warnings are converted to exceptions to make sure they don't get printed)
  * Returned PHP objects are never garbage collected
  * It's probably pretty slow

The bridge works by piping JSON between the Python process and a PHP process.

There are no dependencies, other than PHP 7.0+ and Python 3.5+. Composer can be used to install development tools and set up autoloading, but it's not necessary.
