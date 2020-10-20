from .. import _util
from ..technology import technology_ as tch
from . import layout as lay, circuit as ckt

__all__ = ["Library"]

class _Cell:
    def __init__(self, lib, name):
        assert (
            isinstance(lib, Library)
            and isinstance(name, str)
        ), "Internal error"
        self.lib = lib
        self.name = name

        self.circuits = ckt._Circuits()
        self.layouts = _CellLayouts()

    @property
    def cktfab(self):
        return self.lib.cktfab

    @property
    def circuit(self):
        try:
            return self.circuits[self.name]
        except KeyError:
            raise ValueError(f"Cell '{self.name}' has not default circuit")

    @property
    def layout(self):
        try:
            return self.layouts[self.name]
        except KeyError:
            raise ValueError(f"Cell '{self.name}' has not default layout")

    def new_circuit(self, name=None):
        if name is None:
            name = self.name
        
        circuit = self.cktfab.new_circuit(name)
        self.circuits += circuit
        return circuit

    def add_layout(self, name, layout):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        if not isinstance(layout, lay.Layout):
            raise TypeError("layout has to be of type 'Layout'")

        self.layouts += _CellLayout(name, layout)

    def new_circuitlayouter(self, name=None, *, boundary=None):
        if name is None:
            name = self.name
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        try:
            circuit = self.circuits[name]
        except KeyError:
            raise ValueError(f"circuit with name '{name}' not present")

        layouter = self.lib.layoutfab.new_circuitlayouter(circuit, boundary=boundary)
        self.layouts += _CellLayout(name, layouter.layout)
        return layouter

class _Cells(_util.TypedTuple):
    tt_element_type = _Cell


class _CellLayout:
    def __init__(self, name, layout):
        assert (
            isinstance(name, str)
            and isinstance(layout, lay.Layout)
        ), "Internal error"
        self.name = name
        self.layout = layout


class _CellLayouts(_util.TypedTuple):
    tt_element_type = _CellLayout

    def __getitem__(self, item):
        elem = super().__getitem__(item)
        return elem.layout


class Library:
    def __init__(self, name, *, tech, cktfab=None, layoutfab=None):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        self.name = name

        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type 'Technology'")
        self.tech = tech

        if cktfab is None:
            cktfab = ckt.CircuitFactory(tech)
        elif not isinstance(cktfab, ckt.CircuitFactory):
            raise TypeError("cktfab has to be of type 'CircuitFactory'")
        self.cktfab = cktfab

        if layoutfab is None:
            layoutfab = lay.LayoutFactory(tech)
        elif not isinstance(layoutfab, lay.LayoutFactory):
            raise TypeError("layoutfab has to be of type 'LayoutFactory'")
        self.layoutfab = layoutfab

        self.cells = _Cells()
    
    def new_cell(self, name):
        cell = _Cell(self, name)
        self.cells += cell
        return cell
