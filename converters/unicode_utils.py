import collections
import sys

def to_str(data):
    if sys.version_info >= (3,0):
        return _to_str3(data)
    else:
        return _to_str27(data)

def _to_str3(data):
    if isinstance(data, str):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(to_str, data.items()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(to_str, data))
    else:
        return data

def _to_str27(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(to_str, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(to_str, data))
    else:
        return data