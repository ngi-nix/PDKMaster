# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import abc

from .. import _util
from . import property_ as prp, mask as msk

__all__ = ["MaskEdge"]

class _EdgeProperty(prp.Property):
    def __init__(self, edge, name):
        assert (isinstance(edge, _Edge) and isinstance(name, str)), "Internal error"

        super().__init__(str(edge) + "." + name)
        self.edge = edge
        self.prop_name = name

class _DualEdgeProperty(prp.Property):
    def __init__(self, edge1, edge2, name, *, commutative, allow_mask2):
        assert all((
            isinstance(commutative, bool),
            isinstance(allow_mask2, bool),
            isinstance(edge1, _Edge),
            isinstance(edge2, _Edge) or (isinstance(edge2, msk._Mask) and allow_mask2),
            isinstance(name, str),
        )), "Internal error"

        if commutative:
            full_name = "{}({},{})".format(name, edge1.name, edge2.name)
        else:
            full_name = "{}.{}({})".format(edge1.name, name, edge2.name)
        super().__init__(full_name)

        self.edge1 = edge1
        self.edge2 = edge2
        self.prop_name = name

class _Edge(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name):
        if not isinstance(name, str):
            raise RuntimeError("internal error")
        self.name = name

        self.length = _EdgeProperty(self, "length")

    def __str__(self):
        return self.name

    def enclosed_by(self, other):
        if not isinstance(other, (_Edge, msk._Mask)):
            raise TypeError("other has to be of type '_Edge' or '_Mask'")

        return _DualEdgeProperty(
            self, other, "enclosed_by",
            commutative=False, allow_mask2=True,
        )

    def interact_with(self, other):
        if not isinstance(other, (_Edge, msk._Mask)):
            raise TypeError("other has to be of type '_Edge' or '_Mask'")

        return _DualEdgeOperation(self, other, "interact_with", allow_mask2=True)

class _DualEdgeOperation(_Edge):
    def __init__(self, edge1, edge2, name, allow_mask2=False):
        assert all((
            isinstance(name, str),
            isinstance(edge1, _Edge),
            isinstance(allow_mask2, bool),
            isinstance(edge2, _Edge) or (allow_mask2 and isinstance(edge2, msk._Mask)),
        )), "Internal error"

        super().__init__(name=f"{edge1.name}.{name}({edge2.name})")
        self.edge1 = edge1
        self.edge2 = edge2
        self.operation = name

class MaskEdge(_Edge):
    def __init__(self, mask):
        if not isinstance(mask, msk._Mask):
            raise TypeError("mask has to be of type 'Mask'")
        self.mask = mask

        super().__init__("edge({})".format(mask.name))

class Join(_Edge):
    def __init__(self, edges):
        edges = tuple(edges) if _util.is_iterable(edges) else (edges,)
        if not all(isinstance(edge, _Edge) for edge in edges):
            raise TypeError("edges has to be of type 'Edge' or an iterable of type 'Edge'")

        super().__init__("join({})".format(",".join(str(edge) for edge in edges)))

class Intersect(_Edge):
    def __init__(self, edges):
        if _util.is_iterable(edges):
            edges = tuple(edges)
        else:
            edges = (edges,)
        if not all(isinstance(edge, (msk._Mask, _Edge)) for edge in edges):
            raise TypeError("edges has to be of type 'Mask' or 'Edge' or an iterable of those")
        if not any(isinstance(edge, _Edge) for edge in edges):
            raise ValueError("at least one element of edges has to be of type 'Edge'")
        self.edges = edges

        super().__init__("intersect({})".format(",".join(str(edge) for edge in edges)))
