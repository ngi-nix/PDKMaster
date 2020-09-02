import abc

from .. import _util
from ..technology import (
    property_ as prp, port as prt, primitive as prm, technology_ as tch,
)

__all__ = ["CircuitFactory"]

class _InstancePort:
    def __init__(self, inst, port):
        assert all((
            isinstance(inst, _Instance),
            isinstance(port, prt.Port),
         )), "Internal error"

        self.name = port.name
        self.inst = inst
        self.port = port

class _InstancePorts(_util.TypedTuple):
    tt_element_type = _InstancePort

class _Instance(abc.ABC):
    @abc.abstractmethod
    def __init__(self, name, ports):
        assert all((
            isinstance(name, str),
            isinstance(ports, _InstancePorts),
        )), "Internal error"

        self.name = name
        ports.tt_freeze()
        self.ports = ports

class _Instances(_util.TypedTuple):
    tt_element_type = _Instance

class _PrimitiveInstance(_Instance):
    def __init__(self, name, prim, **params):
        assert all((
            isinstance(name, str),
            isinstance(prim, prm._Primitive),
        )), "Internal error"

        super().__init__(name, _InstancePorts(
            _InstancePort(self, port) for port in prim.ports
        ))

        self.prim = prim
        self.params = params

class _Net:
    def __init__(self, circuit, name, external):
        assert all((
            isinstance(circuit, _Circuit),
            isinstance(name, str),
            isinstance(external, bool),
        )), "Internal error"

        self.circuit = circuit
        self.name = name
        self.ports = _InstancePorts()

    def freeze(self):
        self.ports.tt_freeze()

class _Nets(_util.TypedTuple):
    tt_element_type = _Net

class _NetPort(prt.Port):
    def __init__(self, net):
        assert isinstance(net, _Net), "Internal error"
        super().__init__(net.name)
        self.net = net

class _Circuit:
    def __init__(self, name, fab):
        assert all((
            isinstance(name, str),
            isinstance(fab, CircuitFactory),
        )), "Internal error"
        self.name = name
        self.fab = fab

        self.instances = _Instances()
        self.nets = _Nets()
        self.ports = prt.Ports()

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
        
        net = _Net(self, name, external)
        self.nets += net
        if external:
            self.ports += _NetPort(net)
        return net

class CircuitFactory:
    def __init__(self, tech):
        if not isinstance(tech, tch.Technology):
            raise TypeError("tech has to be of type 'Technology'")
        self.tech = tech

    def new_circuit(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        return _Circuit(name, self)
