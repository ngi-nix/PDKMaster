import abc

from .. import _util

__all__ = ["Port", "Ports"]

class Port(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name):
        assert isinstance(name, str), "Internal error"
        self.name = name

class Ports(_util.TypedTuple):
    tt_element_type = Port
