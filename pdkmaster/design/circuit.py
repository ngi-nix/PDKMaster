# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import abc
from shapely import geometry as sh_geo

from .. import _util
from ..technology import (
    property_ as prp, net as net_, mask as msk, primitive as prm, technology_ as tch,
)
from . import library as lbry

__all__ = ["CircuitFactory"]

class _Instance(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name, ports):
        assert all((
            isinstance(name, str),
            isinstance(ports, net_.Nets),
        )), "Internal error"

        self.name = name
        ports.tt_freeze()
        self.ports = ports

class _InstanceNet(net_.Net):
    def __init__(self, inst, net):
        assert all((
            isinstance(inst, _Instance),
            isinstance(net, net_.Net),
        )), "Internal error"
        super().__init__(net.name)
        self.inst = inst
        self.net = net
        self.full_name = f"{inst.name}.{net.name}"

    def __hash__(self):
        return hash(self.full_name)

    def __eq__(self, other):
        return isinstance(other, _InstanceNet) and ((self.full_name) == other.full_name)

class _InstanceNets(net_.Nets):
    tt_element_type = _InstanceNet
    tt_index_attribute = "full_name"

class _Instances(_util.TypedTuple):
    tt_element_type = _Instance

class _PrimitiveInstance(_Instance):
    def __init__(self, name, prim, **params):
        assert all((
            isinstance(name, str),
            isinstance(prim, prm._Primitive),
        )), "Internal error"

        self.name = name
        super().__init__(
            name, net_.Nets(_InstanceNet(self, port) for port in prim.ports),
        )

        self.prim = prim
        self.params = params

class _CellInstance(_Instance):
    def __init__(self, name, cell, *, circuitname=None):
        assert all((
            isinstance(name, str),
            isinstance(cell, lbry._Cell),
        )), "Internal error"
        self.name = name
        self.cell = cell

        if circuitname is None:
            try:
                circuit = self.cell.circuit
            except AttributeError:
                raise TypeError(
                    "no circuitname provided for cell without default circuit"
                )
        else:
            if not isinstance(circuitname, str):
                raise TypeError("circuitname has to be 'None' or a string")
            self.circtuitname = circuitname
            circuit = cell.circuits[circuitname]
        self.circuit = circuit

        super().__init__(
            name, net_.Nets(_InstanceNet(self, port) for port in circuit.ports),
        )

    # TODO: temporary implementation in wait of better engineered polygon iteration
    # implementation in _Layout
    def net_polygons(self, *, net, layoutname=None):
        if isinstance(net, str):
            try:
                net = self.circuit.nets[net]
            except KeyError:
                raise ValueError(
                    f"net '{net}' does not exist for instance '{self.name}'"
                    f" of cell '{self.cell.name}'"
                )
        if not isinstance(net, net_.Net):
            raise TypeError(
                f"net has to be 'None' or of type 'Net', not {type(net)}"
            )
        if net not in self.circuit.nets:
            raise ValueError(
                f"net '{net.name}' is not a net of instance '{self.name}'"
                f" of cell '{self.cell.name}'"
            )
        layout = None
        if layoutname is None:
            if hasattr(self, "circuitname"):
                try:
                    layout = self.cell.layouts[self.circtuitname]
                except KeyError:
                    pass
        else:
            if not isinstance(layoutname, str):
                raise TypeError(
                    "layoutname has to be 'None' or a string, not of type"
                    f" '{type(layoutname)}'"
                )
            try:
                layout = self.cell.layouts[layoutname]
            except KeyError:
                raise ValueError(
                    f"layout '{layoutname}' does not exist of instance '{selfname}'"
                    f" of cell '{self.cell.name}'"
                )
        if layout is None:
            try:
                layout = self.cell.layout
            except AttributeError:
                raise ValueError(
                    f"cell '{self.cell.name}' of instance '{self.name}'"
                    " does not have a default layout"
                )
        yield from layout.net_polygons(net=net)

class _Circuit:
    def __init__(self, name, fab):
        assert all((
            isinstance(name, str),
            isinstance(fab, CircuitFactory),
        )), "Internal error"
        self.name = name
        self.fab = fab

        self.instances = _Instances()
        self.nets = _CircuitNets()
        self.ports = _CircuitNets()

    def new_instance(self, name, object_, **params):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")

        if isinstance(object_, prm._Primitive):
            params = object_.cast_params(params)
            inst = _PrimitiveInstance(name, object_, **params)
        elif isinstance(object_, lbry._Cell):
            circuitname = params.pop("circuitname", None)
            if params:
                raise NotImplementedError("Parametric Circuit instance")
            inst = _CellInstance(name, object_, circuitname=circuitname)
        else:
            raise TypeError(
                f"object_ has to be of type '_Primitive' or '_Cell', not {type(object_)}",
            )

        self.instances += inst
        return inst

    def new_net(self, name, *, external, childports=None):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        if not isinstance(external, bool):
            raise TypeError("external has to be a bool")
        
        net = _CircuitNet(self, name, external)
        self.nets += net
        if external:
            self.ports += net
        if childports:
            net.childports += childports
        return net

    @property
    def subcells_sorted(self):
        cells = set()
        for inst in self.instances.tt_iter_type(_CellInstance):
            if inst.cell not in cells:
                for subcell in inst.cell.subcells_sorted:
                    if subcell not in cells:
                        yield subcell
                        cells.add(subcell)
                yield inst.cell
                cells.add(inst.cell)

class _Circuits(_util.TypedTuple):
    tt_element_type = _Circuit

class _CircuitNet(net_.Net):
    def __init__(self, circuit, name, external):
        assert all((
            isinstance(circuit, _Circuit),
            isinstance(name, str),
            isinstance(external, bool),
        )), "Internal error"

        super().__init__(name)
        self.circuit = circuit
        self.childports = _InstanceNets()

    def freeze(self):
        self.childports.tt_freeze()

class _CircuitNets(net_.Nets):
    tt_element_type = _CircuitNet

class CircuitFactory:
    def __init__(self, tech):
        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type 'Technology'")
        self.tech = tech

    def new_circuit(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        return _Circuit(name, self)
