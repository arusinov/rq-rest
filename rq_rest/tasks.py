
def default(*args, **kwargs):
    if 'raise_error' in kwargs:
        raise Exception("I`m must raise error")

    return {
        'result': 'ok',
        'log': [],
        'args': args,
        'kwargs': kwargs
    }