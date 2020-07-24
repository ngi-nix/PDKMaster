__all__ = ["i2f"]

def i2f(i):
    "Convert i to float if it is an int but not a bool"
    return float(i) if (isinstance(i, int) and (type(i) != bool)) else i

def is_iterable(it):
    try:
        iter(it)
    except:
        return False
    else:
        return True
