# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from c4m.PySpice.Spice.Netlist import Circuit, SubCircuit
from c4m.PySpice.Unit import u_µm, u_Ω

from ... import _util
from ...technology import primitive as prm
from ...design import circuit as ckt

__all__ = ["PySpiceFactory"]


class _SubCircuit(SubCircuit):
    def __init__(self, circuit, lvs):
        if not isinstance(circuit, ckt._Circuit):
            raise TypeError("circuit has to be of type '_Circuit'")

        ports = tuple(port.name for port in circuit.ports)
        name = circuit.name

        super().__init__(name, *ports)
        self._circuit = circuit

        netlookup = {}
        for net in circuit.nets:
            lookup = dict((port, net) for port in net.childports)
            double = tuple(filter(lambda n: n in netlookup, lookup))
            if double:
                doublenames = tuple(net.full_name for net in double)
                raise ValueError(
                    f"Ports {doublenames} are on more than one net in circuit "
                    f"{circuit.name}"
                )
            netlookup.update(lookup)

        for inst in circuit.instances:
            if isinstance(inst, ckt._PrimitiveInstance):
                if isinstance(inst.prim, prm.MOSFET):
                    sgdb = tuple()
                    for portname in (
                        "sourcedrain1", "gate", "sourcedrain2", "bulk",
                    ):
                        port = inst.ports[portname]
                        try:
                            net = netlookup[port]
                        except KeyError:
                            raise ValueError(
                                f"Port '{port.full_name}' not on any net in circuit "
                                f"'{name}'"
                            )
                        else:
                            sgdb += (net.name,)
                    # TODO: support more instance parameters
                    self.M(inst.name, *sgdb,
                        model=inst.prim.model,
                        l=u_µm(round(inst.params["l"],6)), w=u_µm(round(inst.params["w"],6)),
                    )
                elif isinstance(inst.prim, prm.Resistor):
                    has_model = hasattr(inst.prim, "model")
                    has_sheetres = hasattr(inst.prim, "sheetres")
                    if not (has_model or has_sheetres):
                        raise NotImplementedError(
                            "Resistor circuit generation without a model or sheet resistance"
                        )

                    if has_model and not (has_sheetres and lvs):
                        params = getattr(inst.prim, "model_params", {})
                        model_args = {
                            params["width"]: u_µm(round(inst.params["width"], 6)),
                            params["height"]: u_µm(round(inst.params["height"], 6)),
                        }
                        self.X(
                            inst.name, inst.prim.model,
                            netlookup[inst.ports.port1].name, netlookup[inst.ports.port2].name,
                            **model_args,
                        )
                    else:
                        l = inst.params["height"]
                        w = inst.params["width"]
                        self.R(
                            inst.name,
                            netlookup[inst.ports.port1].name, netlookup[inst.ports.port2].name,
                            u_Ω(round(inst.prim.sheetres*l/w, 4)),
                        )
            elif isinstance(inst, ckt._CellInstance):
                pin_args = tuple()
                for port in inst.ports:
                    try:
                        net = netlookup[port]
                    except KeyError:
                        raise ValueError(
                            f"Port '{port.full_name}' not on any net in circuit "
                            f"'{name}'"
                        )
                    else:
                        pin_args += (net.name,)
                pin_args = tuple(netlookup[port].name for port in inst.ports)
                self.X(inst.name, inst.circuit.name, *pin_args)
            else:
                raise AssertionError("Internal error")


class _Circuit(Circuit):
    def __init__(self, fab, corner, top, title, gnd):
        assert isinstance(fab, PySpiceFactory), "Internal error"

        if title is None:
            title = f"{top.name} testbench"
        super().__init__(title)

        if (not _util.is_iterable(corner)) or (isinstance(corner, str)):
            corner = (corner,)
        else:
            corner = tuple(corner)
        if not all(isinstance(c, str) for c in corner):
            raise TypeError("corner has to be a string or an iterable of strings")
        invalid = tuple(filter(lambda c: c not in fab.corners, corner))
        if invalid:
            raise ValueError(f"Invalid corners(s) {invalid}")
        for c in corner:
            try:
                conflicts = fab.conflicts[c]
            except KeyError:
                pass
            else:
                for c2 in conflicts:
                    if c2 in corner:
                        raise ValueError(
                            f"Corner '{c}' conflicts with corner '{c2}'"
                        )
            self.lib(fab.libfile, c)

        self._fab = fab
        self._corner = corner

        subcircuit = fab.new_pyspicesubcircuit(circuit=top)
        self.subcircuit(subcircuit)
        self.X(
            "top", top.name,
            *(self.gnd if node==gnd else node for node in subcircuit._external_nodes),
        )


class PySpiceFactory:
    def __init__(
        self, *,
        libfile, corners, conflicts,
    ):
        if not isinstance(libfile, str):
            raise TypeError("libfile has to be a string")
        self.libfile = libfile

        corners = set(corners)
        if not all(isinstance(corner, str) for corner in corners):
            raise TypeError("corners has to be an iterable of strings")
        self.corners = corners

        s = (
            "conflicts has to be a dict where the element value is a list of corners\n"
            "that conflict with the key"
        )
        if not isinstance(conflicts, dict):
            raise TypeError(s)
        for key, value in conflicts.items():
            if (key not in corners) or any(c not in corners for c in value):
                raise ValueError(s)
        self.conflicts = conflicts

    def new_pyspicecircuit(self, *, corner, top, title=None, gnd=None):
        return _Circuit(self, corner, top, title, gnd)

    def new_pyspicesubcircuit(self, *, circuit, lvs=False):
        return _SubCircuit(circuit, lvs=lvs)
