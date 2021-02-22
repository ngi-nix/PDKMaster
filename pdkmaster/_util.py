# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import abc
from itertools import islice

__all__ = ["i2f", "is_iterable"]

def i2f(i):
    "Convert i to float if it is an int but not a bool"
    return float(i) if (isinstance(i, int) and (type(i) != bool)) else i

def i2f_recursive(values):
    if is_iterable(values):
        return tuple(i2f_recursive(v) for v in values)
    else:
        return i2f(values)

def v2t(value, *, n=None):
    if is_iterable(value) and (not isinstance(value, str)):
        v = tuple(value)
        if n is not None:
            assert n == len(v)
        return v
    else:
        return (value,) if n is None else tuple(value for _ in range(n))

def is_iterable(it):
    try:
        iter(it)
    except:
        return False
    else:
        return True

def nth(it, n):
    return next(islice(it, n, None))

def first(it):
    return nth(it, 0)

def strip_literal(s):
    if (s[0] == '"') and (s[-1] == '"'):
        return s[1:-1]
    else:
        return s

class TypedTuple(abc.ABC):
    tt_element_type = abc.abstractproperty()
    tt_index_attribute = "name"
    tt_index_type = str

    def __init__(self, elems=tuple()):
        assert (
            isinstance(self.tt_element_type, tuple)
            or (not issubclass(self.tt_element_type, tuple))
        ), "Internal error"
        if isinstance(elems, self.tt_element_type):
            self._t = (elems,)
        else:
            self._t = tuple(elems)
        if not all(isinstance(elem, self.tt_element_type) for elem in self._t):
            raise TypeError(
                f"elements of {self.__class__.__name__} have to be of type {self.tt_element_type.__name__}"
            )

        if self.tt_index_attribute is not None:
            self._d = {
                getattr(elem, self.tt_index_attribute): elem
                for elem in self._t
            }
            if not all(isinstance(key, self.tt_index_type) for key in self._d.keys()):
                raise TypeError(
                    "element index attributes have to be of type "
                    f"{self.tt_index_type.__name__}"
                )

        self._frozen = False

    def tt_freeze(self):
        self._frozen = True

    def tt_reorder(self, neworder):
        neworder = tuple(neworder)
        if set(neworder) != set(range(len(self._t))):
            raise ValueError("neworder has to be iterable of indices with value from 'range(len(self))'")

        self._t = tuple(self._t[i] for i in neworder)

    def index(self, *args, **kwargs):
        return self._t.index(*args, **kwargs)

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._t[key]
        elif isinstance(key, self.tt_index_type) and hasattr(self, "_d"):
            try:
                return self.__getattr__(key)
            except AttributeError:
                raise KeyError(f"'{key}'")
        else:
            raise KeyError(f"'{key}'")

    def __getattr__(self, idx):
        if (self.tt_index_attribute is None) or (idx not in self._d):
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no element with index '{idx}'"
            )
        return self._d[idx]

    def __iadd__(self, other):
        if isinstance(other, self.tt_element_type):
            other = (other,)
        other = tuple(other)
        if not all(isinstance(elem, self.tt_element_type) for elem in other):
            raise TypeError(
                f"elements of {self.__class__.__name__} have to be of type {self.tt_element_type}"
            )
        self._t += other

        if hasattr(self, "_d"):
            d = {
                getattr(elem, self.tt_index_attribute): elem
                for elem in other
            }
            for idx in d.keys():
                if not isinstance(idx, self.tt_index_type):
                    raise TypeError(
                        f"element name attribute value '{idx}' is not "
                        f"of type {self.tt_index_type.__name__}"
                    )
                if idx in self._d:
                    raise ValueError(
                        f"element with index '{idx}' already  present"
                    )
            self._d.update(d)

        return self

    def __iter__(self):
        return iter(self._t)

    def __len__(self):
        return len(self._t)

    def tt_remove(self, elem):
        idx = self.index(elem)
        self._t = self._t[:idx] + self._t[idx+1:]
        if self.tt_index_attribute is not None:
            self._d.pop(getattr(elem, self.tt_index_attribute))

    def tt_pop(self, key):
        elem = self[key]
        self.tt_remove(elem)

        return elem

    def tt_keys(self):
        if not hasattr(self, "_d"):
            raise TypeError("typed tuple elements don't an index")
        return self._d.keys()

    def tt_iter_type(self, type_):
        for elem in self:
            if isinstance(elem, type_):
                yield elem
