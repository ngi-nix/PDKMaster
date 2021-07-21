# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from typing import Any, Callable, Generic, Iterable, Optional, Union, TypeVar, Type

_elem_type = TypeVar("_elem_type")

class SingleOrMulti(Generic[_elem_type]):
    """Type to represent a single value or an iterable of a value of
    a given type.

    Example:
        `SingleOrMulti[int].T` == `Union[int, Interable[int]]`
    """
    T = Union[_elem_type, Iterable[_elem_type]]

class OptSingleOrMulti(Generic[_elem_type]):
    """`OptSingleOrMulti[T].T` == `Optional[SingleOrMulti[T].T]`"""
    T = Optional[Union[_elem_type, Iterable[_elem_type]]]

IntFloat = Union[int, float]
