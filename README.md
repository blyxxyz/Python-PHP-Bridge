Experimental module for calling PHP code from Python.
```python
$ python3 -i client.py
>>> php.fun.array_flip(["foo", "bar"])
{'foo': 0, 'bar': 1}
>>> php.fun.getimagesize("http://php.net/images/logos/new-php-logo.png")
{'0': 200, '1': 106, '2': 3, '3': 'width="200" height="106"', 'bits': 8, 'mime': 'image/png'}
```
