import abc

from .. import _util

__all__ = ["Net", "Nets"]

class Net(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name):
        assert isinstance(name, str), "Internal error"

        self.name = name

class Nets(_util.TypedTuple):
    tt_element_type = Net
