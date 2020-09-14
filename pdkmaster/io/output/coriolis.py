"""Generate coriolis setup file"""
from textwrap import dedent, indent
from itertools import product

from ...technology import (
    primitive as prm, dispatcher as dsp, technology_ as tch,
)

__all__ = ["generate"]

def _str_create_basic(name, mat):
        return (
            f"l = BasicLayer.create(tech, '{name}',"
            f" BasicLayer.Material(BasicLayer.Material.{mat}))\n"
        )

def _str_gds_layer(prim):
    if hasattr(prim, "mask") and hasattr(prim.mask, "gds_layer"):
        mask = prim.mask
        s = f"l.setGds2Layer({mask.gds_layer[0]})\n"
        if mask.gds_layer[1] != 0:
            s += f"l.setGds2Datatype({mask.gds_layer[1]})\n"
        return s
    else:
        return ""

class _LayerGenerator(dsp.PrimitiveDispatcher):
    def __init__(self, tech: tch.Technology):
        # TODO: get the poly layers
        self.poly_layers = set(
            gate.poly for gate in tech.primitives.tt_iter_type(prm.MOSFETGate)
        )
        self.via_conns = via_conns = set()
        for via in tech.primitives.tt_iter_type(prm.Via):
            via_conns.update(via.bottom)
            via_conns.update(via.top)

    def _Primitive(self, prim):
        raise NotImplementedError(
            f"layer code generation for '{prim.__class__.__name__}'"
        )

    def Marker(self, prim):
        return _str_create_basic(prim.name, "other") + _str_gds_layer(prim)

    def ExtraProcess(self, prim):
        return _str_create_basic(prim.name, "other") + _str_gds_layer(prim)

    def Implant(self, prim):
        return _str_create_basic(prim.name, prim.type_+"Implant") + _str_gds_layer(prim)

    def Well(self, prim):
        return _str_create_basic(prim.name, prim.type_+"Well") + _str_gds_layer(prim)

    def WaferWire(self, prim):
        return _str_create_basic(prim.name, "active") + _str_gds_layer(prim)

    def GateWire(self, prim):
        return _str_create_basic(prim.name, "poly") + _str_gds_layer(prim)

    def MetalWire(self, prim):
        return _str_create_basic(prim.name, "metal") + _str_gds_layer(prim)

    def Resistor(self, prim):
        if len(prim.indicator) == 1:
            s_indicator = f"'{prim.indicator[0].name}'"
        else:
            s_indicator = str(tuple(ind.name for ind in prim.indicator))
        return (
            f"# ResistorLayer.create(tech, '{prim.name}', '{prim.wire.name}', "
            f"{s_indicator})\n"
        )

    def Via(self, prim):
        return _str_create_basic(prim.name, "cut") + _str_gds_layer(prim)

    def Auxiliary(self, prim):
        return _str_create_basic(prim.name, "other") + _str_gds_layer(prim)

    def PadOpening(self, prim):
        return _str_create_basic(prim.name, "cut") + _str_gds_layer(prim)

    def MOSFETGate(self, prim):
        s_oxide = f", '{prim.oxide.name}'" if hasattr(prim, "oxide") else ""
        return (
            f"# GateLayer.create(tech, '{prim.name}', '{prim.active.name}', "
            f"'{prim.poly.name}'{s_oxide})\n"
        )

    def MOSFET(self, prim):
        impl_names = tuple(impl.name for impl in prim.implant)
        s_impl = f"'{impl_names[0]}'" if len(impl_names) == 1 else str(impl_names)
        s_well = f", '{prim.well.name}'" if hasattr(prim, "well") else ""
        return (
            f"# TransistorLayer.create(tech, '{prim.name}', '{prim.gate.name}', "
            f"{s_impl}{s_well})\n"
        )

class _AnalogGenerator(dsp.PrimitiveDispatcher):
    def __init__(self, tech):
        self.tech = tech

    def _Primitive(self, prim):
        raise NotImplementedError(
            f"analog code generation for '{prim.__class__.__name__}'"
        )

    def _rows_mask(self, prim):
        s = ""
        if hasattr(prim, "grid"):
            s += f"('grid', '{prim.name}', {prim.grid}, Length, ''),\n"
        return s

    def _rows_widthspace(self, prim):
        s = f"('minWidth', '{prim.name}', {prim.min_width}, Length, ''),\n"
        s += f"('minSpacing', '{prim.name}', {prim.min_space}, Length, ''),\n"
        s += self._rows_mask(prim)
        if hasattr(prim, "min_area"):
            s += f"('minArea', '{prim.name}', {prim.min_area}, Area, ''),\n"
        if hasattr(prim, "min_density"):
            s += f"('minDensity', '{prim.name}', {prim.min_density}, Unit, ''),\n"
        if hasattr(prim, "max_density"):
            s += f"('maxDensity', '{prim.name}', {prim.max_density}, Unit, ''),\n"
        return s

    def Marker(self, prim):
        return self._rows_mask(prim)

    def ExtraProcess(self, prim):
        return self._rows_mask(prim)

    def Auxiliary(self, prim):
        return self._rows_mask(prim)

    def Implant(self, prim):
        return self._rows_widthspace(prim)

    def Well(self, prim):
        s = self._rows_widthspace(prim)
        if hasattr(prim, "min_space_samenet"):
            s += f"('minSpacingSameNet', '{prim.name}', {prim.min_space_samenet}, Length, ''),\n"
        return s

    def Insulator(self, prim):
        return self._rows_widthspace(prim)

    def WaferWire(self, prim):
        s = self._rows_widthspace(prim)
        for i in range(len(prim.well)):
            well = prim.well[i]
            enc = prim.min_well_enclosure[i]
            s += (
                f"('minEnclosure', '{well.name}', '{prim.name}', {enc},"
                " Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_substrate_enclosure"):
            for well in self.tech.primitives.tt_iter_type(prm.Well):
                s += (
                    f"('minSpacing', '{well.name}', '{prim.name}',"
                    f" {prim.min_substrate_enclosure}, ''),\n"
                )
        s += (
            f"# TODO for {prim.name}:\n"
            "#    allow_in_substrate, implant_abut, allow_contactless_implant, allow_well_crossing\n"
        )
        return s

    def GateWire(self, prim):
        return self._rows_widthspace(prim)

    def MetalWire(self, prim):
        # Also handles TopMetalWire
        return self._rows_widthspace(prim)

    def Resistor(self, prim):
        s = self._rows_widthspace(prim)
        for i in range(len(prim.indicator)):
            ind = prim.indicator[i]
            enc = prim.min_enclosure[i]
            s += (
                f"('minEnclosure', '{ind.name}', '{prim.wire.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        return s

    def Via(self, prim):
        s = self._rows_mask(prim)
        s += f"('minWidth', '{prim.name}', {prim.width}, Length, ''),\n"
        s += f"('maxWidth', '{prim.name}', {prim.width}, Length, ''),\n"
        s += f"('minSpacing', '{prim.name}', {prim.min_space}, Length, ''),\n"
        for i in range(len(prim.bottom)):
            bottom = prim.bottom[i]
            enc = prim.min_bottom_enclosure[i]
            s += (
                f"('minEnclosure', '{bottom.name}', '{prim.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        for i in range(len(prim.top)):
            top = prim.top[i]
            enc = prim.min_top_enclosure[i]
            s += (
                f"('minEnclosure', '{top.name}', '{prim.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        return s

    def PadOpening(self, prim):
        s = self._rows_widthspace(prim)
        s += (
            f"('minEnclosure', '{prim.bottom.name}', '{prim.name}', "
            f"{prim.min_bottom_enclosure}, Length|Asymmetric, ''),\n"
        )
        return s

    def Spacing(self, prim):
        return "".join(
            f"('minSpacing', '{prim1.name}', '{prim2.name}', {prim.min_space}, "
            "Length, ''),\n"
            for prim1, prim2 in product(prim.primitives1, prim.primitives2)
        )

    def MOSFETGate(self, prim):
        s = ""
        if hasattr(prim, "min_l"):
            s += f"('minTransistorL', '{prim.name}', {prim.min_l}, Length, ''),\n"
        if hasattr(prim, "min_w"):
            s += f"('minTransistorW', '{prim.name}', {prim.min_w}, Length, ''),\n"
        if hasattr(prim, "min_sd_width"):
            s += (
                f"('minGateExtension', '{prim.active.name}', '{prim.name}', "
                f"{prim.min_sd_width}, Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_polyactive_extension"):
            s += (
                f"('minGateExtension', '{prim.poly.name}', '{prim.name}', "
                f"{prim.min_polyactive_extension}, Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_gate_space"):
            s += (
                f"('minGateSpacing', '{prim.name}', {prim.min_gate_space}, "
                "Length, ''),\n"
            )
        if hasattr(prim, "contact"):
            s += (
                f"('minGateSpacing', '{prim.contact.name}', '{prim.name}', "
                f"{prim.min_gate_space}, Length, ''),\n"
            )
        return s

    def MOSFET(self, prim):
        s = ""
        if hasattr(prim, "min_l"):
            s += f"('transistorMinL', '{prim.name}', {prim.min_l}, Length, ''),\n"
        if hasattr(prim, "min_w"):
            s += f"('transistorMinW', '{prim.name}', {prim.min_w}, Length, ''),\n"
        if hasattr(prim, "min_sd_width"):
            s += (
                f"('minGateExtension', '{prim.active.name}', '{prim.name}', "
                f"{prim.min_sd_width}, Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_polyactive_extension"):
            s += (
                f"('minGateExtension', '{prim.poly.name}', '{prim.name}', "
                f"{prim.min_polyactive_extension}, Length|Asymmetric, ''),\n"
            )
        for i in range(len(prim.implant)):
            impl = prim.implant[i]
            enc = prim.min_gateimplant_enclosure[i]
            s += (
                f"('minGateEnclosure', '{impl.name}', '{prim.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_gate_space"):
            s += (
                f"('minGateSpacing', '{prim.name}', {prim.min_gate_space}, "
                "Length, ''),\n"
            )
        if hasattr(prim, "contact"):
            s += (
                f"('minGateSpacing', '{prim.contact.name}', '{prim.name}', "
                f"{prim.min_gate_space}, Length, ''),\n"
            )
        return s


class CoriolisGenerator:
    def __call__(self, tech):
        return (
            self._s_head()
            + "\n"
            + self._s_technology(tech)
            + "\n"
            + self._s_analog(tech)
        )

    def _s_head(self):
        return dedent(f"""
            import CRL, Hurricane
            from Hurricane import DbU
            from helpers import u
            from helpers.overlay import Configuration
            from helpers.analogtechno import Length, Area, Unit, Asymmetric
        """[1:])
    
    def _s_technology(self, tech):
        gen = _LayerGenerator(tech)

        # Take smallest transistor length as lambda
        lambda_ = min(trans.computed.min_l
            for trans in tech.primitives.tt_iter_type(prm.MOSFET))

        s_head = dedent(f"""
            def init():
                db = Hurricane.DataBase.create()
                CRL.System.get()

                Hurricane.Technology.create('{tech.name}')

                DbU.setPrecision(2)
                DbU.setPhysicalsPerGrid({tech.grid}, DbU.UnitPowerMicro)
                DbU.setGridsPerLambda({round(lambda_/tech.grid)})
                DbU.setSymbolicSnapGridStep(DbU.fromGrid(1.0))
                DbU.setPolygonStep(DbU.fromGrid(1.0))

        """[1:])
                
        s_prims = ""
        written_prims = set()
        
        for waferwire in tech.primitives.tt_iter_type(prm.WaferWire):
            for implant in (*waferwire.implant, *waferwire.well):
                if implant not in written_prims:
                    s_prims += gen(implant)
                    written_prims.add(implant)

        for waferwire in tech.primitives.tt_iter_type(prm.WaferWire):
            assert waferwire not in written_prims
            s_prims += gen(waferwire)
            written_prims.add(waferwire)

        for gatewire in tech.primitives.tt_iter_type(prm.GateWire):
            assert gatewire not in written_prims
            s_prims += gen(gatewire)
            written_prims.add(gatewire)

        for via in tech.primitives.tt_iter_type((prm.Via, prm.PadOpening)):
            assert via not in written_prims
            bottoms = via.bottom if isinstance(via, prm.Via) else (via.bottom,)
            for bottom in bottoms:
                if bottom not in written_prims:
                    s_prims += gen(bottom)
                    written_prims.add(bottom)
            s_prims += gen(via)
            written_prims.add(via)

        extraprocesses = set()
        for res in tech.primitives.tt_iter_type(prm.Resistor):
            extraprocesses.update(res.indicator)
        for proc in extraprocesses:
            s_prims += gen(proc)
        written_prims.update(extraprocesses)

        # Make string for auxiliary primitives, add it at the end.
        s_aux = ""
        for aux in tech.primitives.tt_iter_type(prm.Auxiliary):
            assert aux not in written_prims
            s_aux += gen(aux)
            written_prims.add(aux)

        unhandled_masks = (
            set(prim.name for prim in written_prims)
            - set(mask.name for mask in tech.designmasks)
        )
        if unhandled_masks:
            raise NotImplementedError(f"Layer generation for masks {unhandled_masks} not implemented")

        for prim in tech.primitives.tt_iter_type((prm.Resistor, prm.MOSFETGate, prm.MOSFET)):
            assert prim not in written_prims
            s_prims += gen(prim)
            written_prims.add(prim)

        if s_aux:
            s_prims += "\n# Auxiliary\n" + s_aux

        return s_head + indent(s_prims, prefix="    ")

    def _s_analog(self, tech):
        gen = _AnalogGenerator(tech)

        s = dedent(f"""
            analogTechnologyTable = (
                ('Header', '{tech.name}', DbU.UnitPowerMicro, 'alpha'),
                ('PhysicalGrid', '{tech.grid}', Length, ''),
            
            """[1:]
        )
        s += indent(
            "".join(gen(prim) for prim in tech.primitives),
            prefix="    ",
        )
        s += ")\n"

        return s

generate = CoriolisGenerator()
