# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import abc
from typing import Type, Tuple, Union

from .. import _util


__all__ = ["Net", "Nets"]


class Net(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name):
        assert isinstance(name, str), "Internal error"

        self.name = name

    def __eq__(self, other):
        return isinstance(other, Net) and (self.name == other.name)

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.name})"


class Nets(_util.TypedListStrMapping[Net]):
    _elem_type_: Union[Type[Net], Tuple[Type[Net], ...]] = Net
