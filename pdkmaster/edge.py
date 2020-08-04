import abc

from . import _util, property_ as prp, mask as msk

__all__ = ["MaskEdge"]

class _EdgeProperty(prp.Property):
    def __init__(self, edge, name):
        assert (isinstance(edge, _Edge) and isinstance(name, str)), "Internal error"

        super().__init__(str(edge) + "." + name)
        self.edge = edge
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

        super().__init__("intersect({})".format(",".join(str(edge) for edge in edges)))
