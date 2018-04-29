php_types = {
    'int': int,
    'integer': int,
    'bool': bool,
    'boolean': bool,
    'array': dict,
    'float': float,
    'double': float,
    'string': str
}


def convert_docblock(doc):
    """Strip the comment syntax out of a docblock."""
    if not isinstance(doc, str):
        return doc
    doc = doc.strip('/*')
    lines = doc.split('\n')
    lines = [line.strip() for line in lines]
    lines = [line[1:] if line.startswith('*') else line
             for line in lines]
    return '\n'.join(lines)
