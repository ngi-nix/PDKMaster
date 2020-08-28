import abc

__all__ = ["i2f", "is_iterable"]

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

class TypedTuple(abc.ABC):
    tt_element_type = abc.abstractproperty()
    tt_element_name_attribute = "name"

    def __init__(self, iterable=tuple()):
        assert not issubclass(self.tt_element_type, tuple)
        self._t = tuple(iterable)
        if not all(isinstance(elem, self.tt_element_type) for elem in self._t):
            raise TypeError(
                f"elements of {self.__class__.__name__} have to be of type f{self.tt_element_type.__name__}"
            )

        if self.tt_element_name_attribute is not None:
            self._d = {
                getattr(elem, self.tt_element_name_attribute): elem
                for elem in self._t
            }
            if not all(isinstance(key, str) for key in self._d.keys()):
                raise TypeError("element name attributes have to be strings")

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
        elif isinstance(key, str) and hasattr(self, "_d"):
            return self.__getattr__(key)
        else:
            raise KeyError(f"'{key}'")

    def __getattr__(self, name):
        if (self.tt_element_name_attribute is None) or (name not in self._d):
            raise AttributeError(f"'{self.__class__.__name__}' object has no element with name '{name}'")
        return self._d[name]

    def __iadd__(self, other):
        if isinstance(other, self.tt_element_type):
            other = (other,)
        other = tuple(other)
        if not all(isinstance(elem, self.tt_element_type) for elem in other):
            raise TypeError(
                f"elements of {self.__class__.__name__} have to be of type f{self.tt_element_type}"
            )
        self._t += other

        if hasattr(self, "_d"):
            d = {
                getattr(elem, self.tt_element_name_attribute): elem
                for elem in other
            }
            for name in d.keys():
                if not isinstance(name, str):
                    raise TypeError(f"element name attribute value '{name}' is not a string")
                if name in self._d:
                    raise ValueError(f"element with name '{name}' already  present")
            self._d.update(d)

        return self

    def __iter__(self):
        return iter(self._t)

    def __len__(self):
        return len(self._t)

    def tt_iter_type(self, type_):
        for elem in self:
            if isinstance(elem, type_):
                yield elem
