"""This module is filled with created bridges at runtime.

This helps keeping __module__ sensible, and enables naive name resolution via
__module__ and __qualname__. inspect.getdoc uses it to inherit method
docstrings, and pydoc uses it through inspect.getdoc.
"""

# Looking through this file usually isn't going to do any good
# inspect has trouble with it
__file__ = '<external PHP process>'
