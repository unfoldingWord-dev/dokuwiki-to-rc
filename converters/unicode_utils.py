import collections


def to_str(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(to_str, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(to_str, data))
    else:
        return data