import abc
from shapely import geometry as sh_geo

from .. import _util
from ..technology import (
    property_ as prp, net as net_, mask as msk, primitive as prm, technology_ as tch,
)

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
