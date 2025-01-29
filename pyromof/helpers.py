def check_type(object, type_wanted):
    if not isinstance(object, type_wanted):
        raise TypeError('Expected {0}; got {1}'.format(type_wanted, type(object).__name__))