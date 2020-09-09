import abc
from shapely import geometry as sh_geo

from .. import _util
from ..technology import (
    property_ as prp, net as net_, mask as msk, primitive as prm, technology_ as tch,
)
from . import layout as lay

__all__ = ["CircuitFactory", "CircuitLayouter"]

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
        self.full_name = f"{inst.name}.{net.name}"

    def __hash__(self):
        return hash(self.full_name)

    def __eq__(self, other):
        return isinstance(other, _InstanceNet) and ((self.full_name) == other.full_name)

class _InstanceNets(net_.Nets):
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

class _Circuit:
    def __init__(self, name, fab):
        assert all((
            isinstance(name, str),
            isinstance(fab, CircuitFactory),
        )), "Internal error"
        self.name = name
        self.fab = fab

        self.instances = _Instances()
        self.nets = net_.Nets()
        self.ports = _CircuitNets()
        self._layout = lay.Layout()

    @property
    def layout(self):
        return self._layout

    def new_instance(self, name, object_, **params):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")

        if isinstance(object_, prm._Primitive):
            params = object_.cast_params(params)
        else:
            raise TypeError("object_ has to be of type '_Primitive'")

        inst = _PrimitiveInstance(name, object_, **params)
        self.instances += inst
        return inst

    def new_net(self, name, *, external):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        if not isinstance(external, bool):
            raise TypeError("external has to be a bool")
        
        net = _CircuitNet(self, name, external)
        self.nets += net
        if external:
            self.ports += net
        return net

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
    def __init__(self, tech, layoutfab):
        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type 'Technology'")
        self.tech = tech

        if not isinstance(layoutfab, lay.PrimitiveLayoutFactory):
            raise TypeError("layoutfab has to be of type 'PrimitiveLayoutFactory'")
        self.layout_factory = self.layoutfab = layoutfab

    def new_circuit(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        return _Circuit(name, self)

class CircuitLayouter:
    def __init__(self, circuit):
        if not isinstance(circuit, _Circuit):
            raise TypeError("circuit has to be of type '_Circuit'")
        self.circuit = circuit

    @property
    def tech(self):
        return self.circuit.fab.tech

    @property
    def layoutfab(self):
        return self.circuit.fab.layoutfab

    def place(self, inst, *, x, y):
        if not isinstance(inst, _Instance):
            raise TypeError("inst has to be of type '_Instance'")
        if inst not in self.circuit.instances:
            raise ValueError(
                f"inst '{inst.name}' is not part of circuit '{self.circuit.name}'"
            )
        x = _util.i2f(x)
        y = _util.i2f(y)
        if not all((isinstance(x, float), isinstance(y, float))):
            raise TypeError("x and y have to be floats")

        instlayout = self.layoutfab(
            inst.prim, center=sh_geo.Point(x, y), **inst.params,
        )
        for sublayout in instlayout.sublayouts:
            if isinstance(sublayout, lay.NetSubLayout):
                sublayout.net = _InstanceNet(inst, sublayout.net)
            elif isinstance(sublayout, lay.MultiNetSubLayout):
                for sublayout2 in sublayout.sublayouts:
                    if isinstance(sublayout2, lay.NetSubLayout):
                        sublayout2.net = _InstanceNet(inst, sublayout2.net)

        def _portnets():
            for net in self.circuit.nets:
                for port in net.childports:
                    yield (port, net)
        portnets = dict(_portnets())

        def connect_ports(sublayouts):
            for sublayout in sublayouts:
                if isinstance(sublayout, lay.NetSubLayout):
                    try:
                        net = portnets[sublayout.net]
                    except KeyError:
                        net = _InstanceNet(inst, sublayout.net)
                    sublayout.net = net
                elif isinstance(sublayout, lay.MultiNetSubLayout):
                    connect_ports(sublayout.sublayouts)
                elif not isinstance(sublayout, lay.NetlessSubLayout):
                    raise AssertionError("Internal error")

        connect_ports(instlayout.sublayouts)
        self.circuit._layout += instlayout.sublayouts


    def connect(self, *, masks=None):
        for polygon in self.circuit._layout.polygons:
            if (masks is not None) and (polygon.mask not in masks):
                continue
            if polygon.mask.fill_space != "no":
                polygon.connect()
