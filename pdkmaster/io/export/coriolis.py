"""Generate coriolis setup file"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from textwrap import dedent, indent
from itertools import product
import shapely.geometry as sh_geo

from ... import _util
from ...technology import (
    primitive as prm, dispatcher as dsp, technology_ as tch,
)
from ...design import layout as lay, library as lbr

__all__ = ["CoriolisGenerator"]

def _str_create_basic(name, mat, *,
    minsize=None, minspace=None, minarea=None, gds_layer=None, gds_datatype=None
):
    s = "createBL(\n"
    s += f"    tech, '{name}', BasicLayer.Material.{mat},\n"
    s_args = []
    if minsize is not None:
        s_args.append(f"size=u({minsize})")
    if minspace is not None:
        s_args.append(f"spacing=u({minspace})")
    if minarea is not None:
        s_args.append(f"area={minarea}")
    if gds_layer is not None:
        s_args.append(f"gds2Layer={gds_layer}")
    if gds_datatype is not None:
        s_args.append(f"gds2DataType={gds_datatype}")
    if s_args:
        s += "    " + ", ".join(s_args) + ",\n"
    s += ")\n"
    return s

def _str_create_via(via):
    assert isinstance(via, prm.Via)

    def _str_bottomtop(bottom, top):
        s_via = f"{bottom.name}_{via.name}_{top.name}"
        return dedent(f"""
            # {bottom.name}<>{via.name}<>{top.name}
            createVia(
                tech, '{s_via}', '{bottom.name}', '{via.name}', '{top.name}',
                u({via.width}),
            )
        """[1:])

    return "".join(_str_bottomtop(bottom, top) for bottom, top in product(
        filter(lambda p: isinstance(p, prm.MetalWire), via.bottom),
        filter(lambda p: isinstance(p, prm.MetalWire), via.top),
    ))

def _args_gds_layer(prim):
    if hasattr(prim, "mask") and hasattr(prim.mask, "gds_layer"):
        gds_layer = prim.mask.gds_layer
        return {"gds_layer": gds_layer[0], "gds_datatype": gds_layer[1]}
    else:
        return {}

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
        self.blockages = set(prim.blockage for prim in filter(
            lambda p: hasattr(p, "blockage"), tech.primitives,
        ))

    def _Primitive(self, prim):
        raise NotImplementedError(
            f"layer code generation for '{prim.__class__.__name__}'"
        )

    def Marker(self, prim):
        type_ = "blockage" if prim in self.blockages else "other"
        return _str_create_basic(prim.name, type_, **_args_gds_layer(prim))

    def ExtraProcess(self, prim):
        return _str_create_basic(prim.name, "other", **_args_gds_layer(prim))

    def Implant(self, prim):
        return _str_create_basic(
            prim.name,
            f"{prim.type_}Implant" if prim.type_ in ("n", "p") else "other",
            minsize=prim.min_width, minspace=prim.min_space,
            minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
            **_args_gds_layer(prim),
        )

    def Well(self, prim):
        return _str_create_basic(
            prim.name, prim.type_+"Well",
            minsize=prim.min_width, minspace=prim.min_space,
            minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
            **_args_gds_layer(prim),
        )

    def Insulator(self, prim):
        return _str_create_basic(prim.name, "other", **_args_gds_layer(prim))

    def WaferWire(self, prim):
        return _str_create_basic(
            prim.name, "active",
            minsize=prim.min_width, minspace=prim.min_space,
            minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
            **_args_gds_layer(prim),
        )

    def GateWire(self, prim):
        return _str_create_basic(
            prim.name, "poly",
            minsize=prim.min_width, minspace=prim.min_space,
            minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
            **_args_gds_layer(prim),
        )

    def MetalWire(self, prim):
        return _str_create_basic(
            prim.name, "metal",
            minsize=prim.min_width, minspace=prim.min_space,
            minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
            **_args_gds_layer(prim),
        )

    def Via(self, prim, *, via_layer=False):
        if via_layer:
            return _str_create_via(prim)
        else:
            return _str_create_basic(
                prim.name, "cut",
                minsize=prim.width, minspace=prim.min_space,
                minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
                **_args_gds_layer(prim),
            )

    def Auxiliary(self, prim):
        return indent(
            _str_create_basic(prim.name, "other", **_args_gds_layer(prim)),
            prefix="# ",
        )

    def PadOpening(self, prim):
        return _str_create_basic(
            prim.name, "cut",
            minsize=prim.min_width, minspace=prim.min_space,
            minarea=(None if not hasattr(prim, "min_area") else prim.min_area),
            **_args_gds_layer(prim),
        )

    def Resistor(self, prim):
        if len(prim.indicator) == 1:
            s_indicator = f"'{prim.indicator[0].name}'"
        else:
            s_indicator = str(tuple(ind.name for ind in prim.indicator))
        return (
            f"# ResistorLayer.create(tech, '{prim.name}', '{prim.wire.name}', "
            f"{s_indicator})\n"
        )

    def Diode(self, prim):
        if len(prim.indicator) == 1:
            s_indicator = f"'{prim.indicator[0].name}'"
        else:
            s_indicator = str(tuple(ind.name for ind in prim.indicator))
        return (
            f"# DiodeLayer.create(tech, '{prim.name}', '{prim.wire.name}', "
            f"{s_indicator})\n"
        )

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
            enc = prim.min_well_enclosure[i].spec
            s += (
                f"('minEnclosure', '{well.name}', '{prim.name}', {enc},"
                " Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_substrate_enclosure"):
            for well in self.tech.primitives.tt_iter_type(prm.Well):
                s += (
                    f"('minSpacing', '{well.name}', '{prim.name}', "
                    f" {prim.min_substrate_enclosure.spec}, Length|Asymmetric, ''),\n"
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

    def Via(self, prim):
        s = self._rows_mask(prim)
        s += f"('minWidth', '{prim.name}', {prim.width}, Length, ''),\n"
        s += f"('maxWidth', '{prim.name}', {prim.width}, Length, ''),\n"
        s += f"('minSpacing', '{prim.name}', {prim.min_space}, Length, ''),\n"
        for i in range(len(prim.bottom)):
            bottom = prim.bottom[i]
            enc = prim.min_bottom_enclosure[i].spec
            s += (
                f"('minEnclosure', '{bottom.name}', '{prim.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        for i in range(len(prim.top)):
            top = prim.top[i]
            enc = prim.min_top_enclosure[i].spec
            s += (
                f"('minEnclosure', '{top.name}', '{prim.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        return s

    def PadOpening(self, prim):
        s = self._rows_widthspace(prim)
        s += (
            f"('minEnclosure', '{prim.bottom.name}', '{prim.name}', "
            f"{prim.min_bottom_enclosure.spec}, Length|Asymmetric, ''),\n"
        )
        return s

    def Resistor(self, prim):
        s = self._rows_widthspace(prim)
        for i in range(len(prim.indicator)):
            ind = prim.indicator[i]
            enc = prim.min_indicator_extension[i]
            s += (
                f"('minEnclosure', '{ind.name}', '{prim.wire.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        s = indent(s, prefix="# ")
        return s

    def Diode(self, prim):
        s = self._rows_widthspace(prim)
        for i in range(len(prim.indicator)):
            ind = prim.indicator[i]
            enc = prim.min_indicator_enclosure[i]
            s += (
                f"('minEnclosure', '{ind.name}', '{prim.wire.name}', {enc.spec}, "
                "Length|Asymmetric, ''),\n"
            )
        s = indent(s, prefix="# ")
        return s

    def MOSFETGate(self, prim):
        s = ""
        if hasattr(prim, "min_l"):
            s += f"# ('minTransistorL', '{prim.name}', {prim.min_l}, Length, ''),\n"
        if hasattr(prim, "min_w"):
            s += f"# ('minTransistorW', '{prim.name}', {prim.min_w}, Length, ''),\n"
        if hasattr(prim, "min_sd_width"):
            s += (
                f"# ('minGateExtension', '{prim.active.name}', '{prim.name}', "
                f"{prim.min_sd_width}, Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_polyactive_extension"):
            s += (
                f"# ('minGateExtension', '{prim.poly.name}', '{prim.name}', "
                f"{prim.min_polyactive_extension}, Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_gate_space"):
            s += (
                f"# ('minGateSpacing', '{prim.name}', {prim.min_gate_space}, "
                "Length, ''),\n"
            )
        if hasattr(prim, "contact"):
            s += (
                f"# ('minGateSpacing', '{prim.contact.name}', '{prim.name}', "
                f"{prim.min_contactgate_space}, Length|Asymmetric, ''),\n"
            )
        return s

    def MOSFET(self, prim):
        s = ""
        if hasattr(prim, "min_l"):
            s += f"# ('minTransistorL', '{prim.name}', {prim.min_l}, Length, ''),\n"
        if hasattr(prim, "min_w"):
            s += f"# ('minTransistorW', '{prim.name}', {prim.min_w}, Length, ''),\n"
        if hasattr(prim, "min_sd_width"):
            s += (
                f"# ('minGateExtension', '{prim.active.name}', '{prim.name}', "
                f"{prim.min_sd_width}, Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_polyactive_extension"):
            s += (
                f"# ('minGateExtension', '{prim.poly.name}', '{prim.name}', "
                f"{prim.min_polyactive_extension}, Length|Asymmetric, ''),\n"
            )
        for i in range(len(prim.implant)):
            impl = prim.implant[i]
            enc = prim.min_gateimplant_enclosure[i].spec
            s += (
                f"# ('minGateEnclosure', '{impl.name}', '{prim.name}', {enc}, "
                "Length|Asymmetric, ''),\n"
            )
        if hasattr(prim, "min_gate_space"):
            s += (
                f"# ('minGateSpacing', '{prim.name}', {prim.min_gate_space}, "
                "Length, ''),\n"
            )
        if hasattr(prim, "contact"):
            s += (
                f"# ('minGateSpacing', '{prim.contact.name}', '{prim.name}', "
                f"{prim.min_gate_space}, Length, ''),\n"
            )
        return s

    def Spacing(self, prim):
        return "".join(
            f"('minSpacing', '{prim1.name}', '{prim2.name}', {prim.min_space}, "
            "Length|Asymmetric, ''),\n"
            for prim1, prim2 in product(prim.primitives1, prim.primitives2)
        )


class _LibraryGenerator:
    def __init__(self, tech):
        assert isinstance(tech, tch.Technology)
        self.tech = tech
        self.metals = tuple(tech.primitives.tt_iter_type(prm.MetalWire))
        self.vias = tuple(tech.primitives.tt_iter_type(prm.Via))
        assert len(self.metals) == len(self.vias)
        self.pinmasks = pinmasks = {}
        for prim in filter(lambda p: hasattr(p, "pin"), tech.primitives):
            pinmasks.update({p.mask: prim.mask for p in prim.pin})

    def __call__(self, lib):
        assert isinstance(lib, lbr.Library)
        return "\n".join((
            self._s_head(), self._s_routing(lib), self._s_load(lib),
            self._s_setup(lib),
        ))

    def _s_head(self):
        return dedent(f"""
            # Autogenerated file. Changes will be overwritten.

            import CRL, Hurricane, Viewer, Cfg
            from Hurricane import (
                Technology, DataBase, DbU, Library,
                Layer, BasicLayer,
                Cell, Net, Vertical, Rectilinear, Box, Point,
                Instance, Transformation,
                NetExternalComponents,
            )
            from common.colors import toRGB
            from common.patterns import toHexa
            from helpers import u, l
            from helpers.technology import setEnclosures
            from helpers.overlay import CfgCache, UpdateSession

            __all__ = ["setup"]

            def createRL(tech, net, layer, coords):
                coords = [Point(u(x), u(y)) for x,y in coords]
                Rectilinear.create(net, tech.getLayer(layer), coords)
        """[1:])

    def _s_setup(self, lib):
        return dedent(f"""
            def setup():
                lib = _load()
                _routing()
                try:
                    from {lib.name}_fix import fix
                except:
                    pass
                else:
                    fix(lib)

                return lib
        """[1:])

    def _s_routing(self, lib):
        s = dedent(f"""
            def _routing():
                af = CRL.AllianceFramework.get()
                db = DataBase.getDB()
                tech = db.getTechnology()

        """[1:])

        if isinstance(lib, lbr.StdCellLibrary):
            s += indent(
                "\n".join(
                    (self._s_gauge(lib), self._s_pnr(lib), self._s_plugins())
                ),
                prefix="    ",
            )
        else:
            s += "    # No standard cell library\n    pass\n"

        return s

    def _s_gauge(self, lib):
        def otherdir(dir_):
            return "vertical" if dir_ == "horizontal" else "horizontal"
        def s_cordir(dir_):
            return (
                "CRL.RoutingLayerGauge.Horizontal" if dir_ == "horizontal"
                else "CRL.RoutingLayerGauge.Vertical"
            )

        assert len(lib.routinggauge) == 1
        rg = lib.routinggauge[0]
        s = dedent(f"""
            rg = CRL.RoutingGauge.create('{lib.name}')
            rg.setSymbolic(False)
        """[1:])
        bottom_idx = self.metals.index(rg.bottom)
        top_idx = self.metals.index(rg.top)

        depth = 0
        for i in range(max(bottom_idx - 1, 0), top_idx+1):
            routedir = rg.bottom_direction
            if i < bottom_idx:
                s_usage = "CRL.RoutingLayerGauge.PinOnly"
            else:
                s_usage = "CRL.RoutingLayerGauge.Default"
                # Take opposite direction for offset of layer number
                if ((i - bottom_idx) % 2) == 1:
                    routedir = otherdir(routedir)

            metal = self.metals[i]
            s += f"metal = tech.getLayer('{metal.name}')\n"
            mwidth = round(
                self.tech.computed.min_width(
                    metal, up=True, down=True, min_enclosure=(i < bottom_idx),
                ), 6,
            )
            mpwidth = round(
                self.tech.computed.min_width(
                    metal, up=False, down=True, min_enclosure=True
                ), 6,
            )
            if i >= bottom_idx:
                mpitch = round(
                    rg.pitches.get(
                        metal,
                        self.tech.computed.min_pitch(metal, up=True, down=True),
                    ),
                    6,
                )
                offset = rg.offsets.get(metal, 0.0)
            else:
                # For pin only layer take pitch/offset of two levels up
                altmetal = self.metals[i+2]
                mpitch = round(
                    rg.pitches.get(
                        altmetal,
                        self.tech.computed.min_pitch(altmetal, up=True, down=True),
                    ),
                    6,
                )
                offset = rg.offsets.get(altmetal, 0.0)
            s_pindir = s_cordir(routedir)
            dw = metal.min_space

            # Via below
            if i > 0:
                via = self.vias[i]
                metal_idx = via.top.index(metal)
                enc = via.min_top_enclosure[metal_idx]
                metal2 = self.metals[i-1]
                via_name = f"{metal2.name}_{via.name}_{metal.name}"
                if routedir == "horizontal":
                    henc = enc.min()
                    venc = enc.max()
                else:
                    henc = enc.max()
                    venc = enc.min()
                s += dedent(f"""
                    via = tech.getLayer('{via_name}')
                    setEnclosures(via, metal, (u({henc}), u({venc})))
                """[1:])
                vwidth = via.width

            # Via above (only if it exists)
            if i < (len(self.vias) - 1):
                via = self.vias[i + 1]
                metal_idx = via.bottom.index(metal)
                enc = via.min_bottom_enclosure[metal_idx]
                metal2 = self.metals[i+1]
                via_name = f"{metal.name}_{via.name}_{metal2.name}"
                if routedir == "horizontal":
                    henc = enc.min()
                    venc = enc.max()
                else:
                    henc = enc.max()
                    venc = enc.min()
                s += dedent(f"""
                    via = tech.getLayer('{via_name}')
                    setEnclosures(via, metal, (u({henc}), u({venc})))
                """[1:])
                vwidth = via.width

            s += dedent(f"""
                rg.addLayerGauge(CRL.RoutingLayerGauge.create(
                    metal, {s_pindir}, {s_usage}, {depth}, 0.0,
                    u({offset}), u({mpitch}), u({mwidth}), u({mpwidth}), u({vwidth}), u({dw}),
                ))
            """[1:])

            depth += 1

        s += dedent(f"""
            af.addRoutingGauge(rg)
            af.setRoutingGauge('{lib.name}')

            cg = CRL.CellGauge.create(
                '{lib.name}', '{self.metals[1].name}',
                u({lib.pingrid_pitch}), u({lib.row_height}), u({lib.pingrid_pitch}),
            )
            af.addCellGauge(cg)
            af.setCellGauge('{lib.name}')
        """[1:])

        return s

    def _s_pnr(self, lib):
        topmetal = tuple(self.tech.primitives.tt_iter_type(prm.MetalWire))[-1]
        return dedent(f"""
            # Place & Route setup
            with CfgCache(priority=Cfg.Parameter.Priority.ConfigurationFile) as cfg:
                cfg.lefImport.minTerminalWidth = 0.0
                cfg.crlcore.groundName = 'vss'
                cfg.crlcore.powerName = 'vdd'
                cfg.etesian.aspectRatio = 1.00
                cfg.etesian.aspectRatio = [10, 1000]
                cfg.etesian.spaceMargin = 0.10
                cfg.etesian.uniformDensity = False
                cfg.etesian.routingDriven = False
                cfg.etesian.feedNames = 'tie_x0,fill_x0'
                cfg.etesian.cell.zero = 'zero_x0'
                cfg.etesian.cell.one = 'one_x0'
                cfg.etesian.bloat = 'disabled'
                cfg.etesian.effort = 2
                cfg.etesian.effort = (
                    ('Fast', 1),
                    ('Standard', 2),
                    ('High', 3 ),
                    ('Extreme', 4 ),
                )
                cfg.etesian.graphics = 2
                cfg.etesian.graphics = (
                    ('Show every step', 1),
                    ('Show lower bound', 2),
                    ('Show result only', 3),
                )
                cfg.anabatic.routingGauge = '{lib.name}'
                cfg.anabatic.globalLengthThreshold = 1450
                cfg.anabatic.saturateRatio = 90
                cfg.anabatic.saturateRp = 10
                cfg.anabatic.topRoutingLayer = '{topmetal.name}'
                cfg.anabatic.edgeLength = 48
                cfg.anabatic.edgeWidth = 8
                cfg.anabatic.edgeCostH = 9.0
                cfg.anabatic.edgeCostK = -10.0
                cfg.anabatic.edgeHInc = 1.0
                cfg.anabatic.edgeHScaling = 1.0
                cfg.anabatic.globalIterations = 10
                cfg.anabatic.globalIterations = [ 1, 100 ]
                cfg.anabatic.gcell.displayMode = 1
                cfg.anabatic.gcell.displayMode = (("Boundary", 1), ("Density", 2))
                cfg.katana.hTracksReservedLocal = 4
                cfg.katana.hTracksReservedLocal = [0, 20]
                cfg.katana.vTracksReservedLocal = 3
                cfg.katana.vTracksReservedLocal = [0, 20]
                cfg.katana.termSatReservedLocal = 8
                cfg.katana.termSatThreshold = 9
                cfg.katana.eventsLimit = 4000002
                cfg.katana.ripupCost = 3
                cfg.katana.ripupCost = [0, None]
                cfg.katana.strapRipupLimit = 16
                cfg.katana.strapRipupLimit = [1, None]
                cfg.katana.localRipupLimit = 9
                cfg.katana.localRipupLimit = [1, None]
                cfg.katana.globalRipupLimit = 5
                cfg.katana.globalRipupLimit = [1, None]
                cfg.katana.longGlobalRipupLimit = 5
                cfg.chip.padCoreSide = 'South'
        """[1:])

    def _s_plugins(self):
        return dedent(f"""
            # Plugins setup
            with CfgCache(priority=Cfg.Parameter.Priority.ConfigurationFile) as cfg:
                cfg.chip.block.rails.count = 5
                cfg.chip.block.rails.hWidth = u(2.68)
                cfg.chip.block.rails.vWidth = u(2.68)
                cfg.chip.block.rails.hSpacing = u(0.7)
                cfg.chip.block.rails.vSpacing = u(0.7)
                cfg.clockTree.minimumSide = l(600)
                cfg.clockTree.buffer = 'buf_x2'
                cfg.clockTree.placerEngine = 'Etesian'
                cfg.block.spareSide = 10
                cfg.spares.buffer = 'buf_x8'
                cfg.spares.maxSinks = 31
        """[1:])

    def _s_load(self, lib):
        s = dedent(f"""
            def _load():
                af = CRL.AllianceFramework.get()
                db = DataBase.getDB()
                tech = db.getTechnology()
                rootlib = db.getRootLibrary()

                lib = Library.create(rootlib, '{lib.name}')
        """)

        s += indent(
            "".join(self._s_cell(lib, cell) for cell in lib.cells),
            prefix="    ",
        )

        s += indent(dedent("""
            af.wrapLibrary(lib, 0)

            return lib
        """), prefix="    ")

        return s

    def _s_cell(self, lib, cell):
        try:
            s = dedent(f"""
                cell = Cell.create(lib, '{cell.name}')
                with UpdateSession():
            """)

            if hasattr(cell, "layout"):
                layout = cell.layout
                bnd = layout.boundary
                assert bnd is not None, f"Cell boundary needed for {cell.name}"

                pls = tuple(layout.sublayouts.tt_iter_type(
                    (lay.NetSubLayout, lay.MultiNetSubLayout, lay.NetlessSubLayout),
                ))
                def get_netname(sl):
                    if isinstance(sl, lay.NetSubLayout):
                        return sl.net.name
                    elif isinstance(sl, (
                        lay.MultiNetSubLayout, lay.NetlessSubLayout,
                    )):
                        return "*"
                    else:
                        raise AssertionError("Internal error: unhandled sublayout type")

                netnames = set(get_netname(sl) for sl in pls)

                s += (
                    "    cell.setAbutmentBox(Box(\n"
                    f"        u({bnd.left}), u({bnd.bottom}), u({bnd.right}), u({bnd.top}),\n"
                    "    ))\n"
                    "    nets = {\n"
                    + "\n".join(
                        f"        '{net}': Net.create(cell, '{net}'),"
                        for net in sorted(netnames)
                    )
                    + "\n    }\n"
                )

                if hasattr(lib, "global_nets"):
                    for net in netnames:
                        if net in lib.global_nets:
                            s += f"    nets['{net}'].setGlobal(True)\n"

                for sl in pls:
                    s += indent(
                        f"net = nets['{get_netname(sl)}']\n" +
                        "".join(
                            self._s_polygon(mp.mask, mp.polygon)
                            for mp in sl.polygons
                        ),
                        prefix="    ",
                    )

                for sl in layout.sublayouts.tt_iter_type(lay._InstanceSubLayout):
                    # Currently usage of af.getCell() may not work as intended when
                    # two libraries have a cell with the same name.
                    # TODO: support libraries with cells with same name properly
                    r = {
                        "no": "ID",
                        "90": "R1",
                        "180": "R2",
                        "270": "R3",
                        "mirrorx": "MX",
                        "mirrorx&90": "XR",
                        "mirrory": "MY",
                        "mirrory&90": "YR",
                    }[sl.rotation]
                    s += indent(
                        dedent(f"""
                            subcell = lib.getCell('{sl.inst.cell.name}')
                            if subcell is None:
                                subcell = af.getCell('{sl.inst.cell.name}', 0)
                            trans = Transformation(
                                u({sl.x}), u({sl.y}), Transformation.Orientation.{r},
                            )
                            Instance.create(
                                cell, '{sl.inst.name}', subcell, trans,
                                Instance.PlacementStatus.PLACED,
                            )
                        """[1:]),
                        prefix = "    "
                    )
            return s
        except NotImplementedError:
            return f"# Export failed for cell '{cell.name}'"

    def _s_polygon(self, mask, polygon):
        if isinstance(polygon, sh_geo.MultiPolygon):
            return "".join(
                self._s_polygon(mask, poly2)
                for poly2 in polygon
            )
        elif isinstance(polygon, sh_geo.Polygon):
            p = polygon.simplify(0.000001)
            coords = tuple(p.exterior.coords)
            ints = tuple(p.interiors)
            if not ints:
                if mask in self.pinmasks:
                    metalmask = self.pinmasks[mask]
                    if len(coords) == 6:
                        c0 = coords[0]
                        c1 = coords[1]
                        c4 = coords[-2]
                        c5 = coords[-1]
                        if (
                            (c0[0] == c1[0] == c4[0] == c5[0])
                            or (c0[1] == c1[1] == c4[1] == c5[1])
                        ):
                            coords = coords[1:-1] + coords[1:2]
                    if len(coords) != 5:
                        raise NotImplementedError(
                            f"Non-rectangular pin with coords '{coords}'"
                        )
                    xs = tuple(coord[0] for coord in coords)
                    ys = tuple(coord[1] for coord in coords)
                    left = min(xs)
                    right = max(xs)
                    bottom = round(min(ys), 6)
                    top = round(max(ys), 6)
                    x = round(0.5*(left + right), 6)
                    width = round(right - left, 6)
                    s = dedent(f"""
                        Vertical.create(
                            net, tech.getLayer('{mask.name}'),
                            u({x}), u({width}), u({bottom}), u({top}),
                        )
                        pin = Vertical.create(
                            net, tech.getLayer('{metalmask.name}'),
                            u({x}), u({width}), u({bottom}), u({top}),
                        )
                        net.setExternal(True)
                        NetExternalComponents.setExternal(pin)
                    """[1:])
                else:
                    s = dedent(f"""
                        createRL(
                            tech, net, '{mask.name}',
                            ({",".join(self._s_point(point) for point in coords)}),
                        )
                    """[1:])
            elif len(ints) == 1:
                incoords = tuple(ints[0].coords)
                if (len(coords) == 5) and (len(incoords) == 5):
                    # Assume outer and inner are boxes
                    out_left, out_bottom, out_right, out_top = p.exterior.bounds
                    in_left, in_bottom, in_right, in_top = ints[0].bounds
                    coords2 = (
                        (out_left, out_bottom), (out_right, out_bottom),
                        (out_right, out_top), (out_left, out_top),
                        (out_left, in_bottom), (in_left, in_bottom),
                        (in_left, in_top), (in_right, in_top),
                        (in_right, in_top), (in_right, in_bottom),
                        (out_left, in_bottom), (out_left, out_bottom),
                    )
                    s = dedent(f"""
                        createRL(
                            tech, net, '{mask.name}',
                            ({",".join(self._s_point(point) for point in coords2)}),
                        )
                    """[1:])
                else:
                    raise NotImplementedError(
                        "unsupported shapely polygon with an interior"
                    )
            else:
                raise NotImplementedError(
                    "shapely polygon with multiple interiors"
                )

        return s

    def _s_point(self, point):
        assert (
            isinstance(point, tuple) and (len(point) == 2)
        )
        # TODO: put on grid
        x = round(point[0], 6)
        y = round(point[1], 6)

        return f"({x},{y})"


class _TechnologyGenerator:
    def __call__(self, tech):
        assert isinstance(tech, tch.Technology)
        self.tech = tech

        return "\n".join((
            self._s_head(), self._s_analog(), self._s_technology(),
            self._s_display(), self._s_setup(),
        ))

    def _s_head(self):
        return dedent(f"""
            # Autogenerated file. Changes will be overwritten.

            import CRL, Hurricane, Viewer, Cfg
            from Hurricane import (
                Technology, DataBase, DbU, Library,
                Layer, BasicLayer,
                Cell, Net, Vertical, Rectilinear, Box, Point,
                NetExternalComponents,
            )
            from common.colors import toRGB
            from common.patterns import toHexa
            from helpers import u
            from helpers.technology import createBL, createVia
            from helpers.overlay import CfgCache
            from helpers.analogtechno import Length, Area, Unit, Asymmetric, loadAnalogTechno

            __all__ = ["analogTechnologyTable", "setup"]
        """[1:])

    def _s_setup(self):
        return dedent(f"""
            def setup():
                _setup_techno()
                _setup_display()
                loadAnalogTechno(analogTechnologyTable, __file__)
                try:
                    from techno_fix import fix
                except:
                    pass
                else:
                    fix()
        """[1:])

    def _s_technology(self):
        gen = _LayerGenerator(self.tech)

        # Take smallest transistor length as lambda
        lambda_ = min(trans.computed.min_l
            for trans in self.tech.primitives.tt_iter_type(prm.MOSFET))

        assert (self.tech.grid % 1e-6) < 1e-9, "Unsupported grid"

        s_head = dedent(f"""
            def _setup_techno():
                db = DataBase.create()
                CRL.System.get()

                tech = Technology.create(db, '{self.tech.name}')

                DbU.setPrecision(2)
                DbU.setPhysicalsPerGrid({self.tech.grid}, DbU.UnitPowerMicro)
                with CfgCache(priority=Cfg.Parameter.Priority.ConfigurationFile) as cfg:
                    cfg.gdsDriver.metricDbu = {1e-6*self.tech.dbu}
                    cfg.gdsDriver.dbuPerUu = {self.tech.dbu}
                DbU.setGridsPerLambda({round(lambda_/self.tech.grid)})
                DbU.setSymbolicSnapGridStep(DbU.fromGrid(1.0))
                DbU.setPolygonStep(DbU.fromGrid(1.0))
                DbU.setStringMode(DbU.StringModePhysical, DbU.UnitPowerMicro)

        """[1:])

        s_prims = ""
        written_prims = set()
        vias = tuple(self.tech.primitives.tt_iter_type(prm.Via))

        for prim in self.tech.primitives:
            # Some primitives are handled later or don't need to be handled
            if isinstance(prim, (
                # Handled by Via
                prm.WaferWire, prm.GateWire, prm.MetalWire,
                # Handled later
                prm.Resistor, prm.Diode, prm.MOSFETGate, prm.MOSFET,
                # Not exported
                prm.Spacing,
            )):
                continue

            # We have to make sure via layers are defined in between top and bottom
            # metal layers
            if isinstance(prim, prm.Via):
                for prim2 in prim.bottom:
                    s_prims += gen(prim2)
                    written_prims.add(prim2)

            # Do not generate layer for Auxiliary layers to avoid having too many
            # layer definitions. Still mark the layer as written.
            if not isinstance(prim, prm.Auxiliary):
                s_prims += gen(prim)
            written_prims.add(prim)

            # For top via also do the top layers
            if isinstance(prim, prm.Via) and prim == vias[-1]:
                for prim2 in prim.top:
                    s_prims += gen(prim2)
                    written_prims.add(prim2)

        # Check if all basic layers were included
        unhandled_masks = (
            set(prim.name for prim in written_prims)
            - set(mask.name for mask in self.tech.designmasks)
        )
        if unhandled_masks:
            raise NotImplementedError(
                f"Layer generation for masks {unhandled_masks} not implemented",
            )

        s_prims += "\n# ViaLayers\n"
        for via in vias:
            s_prims += gen(via, via_layer=True)

        s_prims += "\n# Blockages\n"
        for prim in filter(lambda p: hasattr(p, "blockage"), self.tech.primitives):
            s_prims += dedent(f"""
                tech.getLayer('{prim.name}').setBlockageLayer(
                    tech.getLayer('{prim.blockage.name}')
                )
            """[1:])

        s_prims += "\n# Coriolis internal layers\n"
        for name, mat in (
            ("text.cell", "other"),
            ("text.instance", "other"),
            ("SPL1", "other"),
            ("AutoLayer", "other"),
            ("gmetalh", "metal"),
            ("gcontact", "cut"),
            ("gmetalv", "metal"),
        ):
            s_prims += _str_create_basic(name, mat)

        s_prims += "\n# Resistors\n"
        for prim in self.tech.primitives.tt_iter_type(prm.Resistor):
            assert prim not in written_prims
            s_prims += gen(prim)
            written_prims.add(prim)

        s_prims += "\n# Transistors\n"
        for prim in self.tech.primitives.tt_iter_type((prm.MOSFETGate, prm.MOSFET)):
            assert prim not in written_prims
            s_prims += gen(prim)
            written_prims.add(prim)

        return s_head + indent(s_prims, prefix="    ")

    def _s_analog(self):
        gen = _AnalogGenerator(self.tech)

        s = dedent(f"""
            analogTechnologyTable = (
                ('Header', '{self.tech.name}', DbU.UnitPowerMicro, 'alpha'),
                ('PhysicalGrid', {self.tech.grid}, Length, ''),
            
            """[1:]
        )
        s += indent(
            "".join(gen(prim) for prim in self.tech.primitives),
            prefix="    ",
        )
        s += ")\n"

        return s

    def _s_display(self):
        s = dedent("""
            def _setup_display():
                # ----------------------------------------------------------------------
                # Style: Alliance.Classic [black]

                threshold = 0.2 if Viewer.Graphics.isHighDpi() else 0.1

                style = Viewer.DisplayStyle( 'Alliance.Classic [black]' )
                style.setDescription( 'Alliance Classic Look - black background' )
                style.setDarkening  ( Viewer.DisplayStyle.HSVr(1.0, 3.0, 2.5) )

                # Viewer.
                style.addDrawingStyle( group='Viewer', name='fallback'      , color=toRGB('Gray238'    ), border=1, pattern='55AA55AA55AA55AA' )
                style.addDrawingStyle( group='Viewer', name='background'    , color=toRGB('Gray50'     ), border=1 )
                style.addDrawingStyle( group='Viewer', name='foreground'    , color=toRGB('White'      ), border=1 )
                style.addDrawingStyle( group='Viewer', name='rubber'        , color=toRGB('192,0,192'  ), border=4, threshold=0.02 )
                style.addDrawingStyle( group='Viewer', name='phantom'       , color=toRGB('Seashell4'  ), border=1 )
                style.addDrawingStyle( group='Viewer', name='boundaries'    , color=toRGB('208,199,192'), border=1, pattern='0000000000000000', threshold=0 )
                style.addDrawingStyle( group='Viewer', name='marker'        , color=toRGB('80,250,80'  ), border=1 )
                style.addDrawingStyle( group='Viewer', name='selectionDraw' , color=toRGB('White'      ), border=1 )
                style.addDrawingStyle( group='Viewer', name='selectionFill' , color=toRGB('White'      ), border=1 )
                style.addDrawingStyle( group='Viewer', name='grid'          , color=toRGB('White'      ), border=1, threshold=2.0 )
                style.addDrawingStyle( group='Viewer', name='spot'          , color=toRGB('White'      ), border=2, threshold=6.0 )
                style.addDrawingStyle( group='Viewer', name='ghost'         , color=toRGB('White'      ), border=1 )
                style.addDrawingStyle( group='Viewer', name='text.ruler'    , color=toRGB('White'      ), border=1, threshold=  0.0 )
                style.addDrawingStyle( group='Viewer', name='text.instance' , color=toRGB('White'      ), border=1, threshold=400.0 )
                style.addDrawingStyle( group='Viewer', name='text.reference', color=toRGB('White'      ), border=1, threshold=200.0 )
                style.addDrawingStyle( group='Viewer', name='undef'         , color=toRGB('Violet'     ), border=0, pattern='2244118822441188' )
        """[1:])

        clrs = ("Blue", "Aqua", "LightPink", "Green", "Yellow", "Violet", "Red")

        s += "\n    # Active Layers.\n"
        for prim in self.tech.primitives.tt_iter_type(prm.Well):
            rgb = "Tan" if prim.type_ == "n" else "LightYellow"
            s += (
                f"    style.addDrawingStyle(group='Active Layers', name='{prim.name}'"
                f", color=toRGB('{rgb}'), pattern=toHexa('urgo.8'), border=1"
                ", threshold=threshold)\n"
            )
        for prim in filter(
            lambda p: isinstance(p, prm.Implant) and not isinstance(p, prm.Well),
            self.tech.primitives,
        ):
            rgb = "LawnGreen" if prim.type_ == "n" else "Yellow"
            s += (
                f"    style.addDrawingStyle(group='Active Layers', name='{prim.name}'"
                f", color=toRGB('{rgb}'), pattern=toHexa('antihash0.8'), border=1"
                ", threshold=threshold)\n"
            )
        for prim in self.tech.primitives.tt_iter_type(prm.WaferWire):
            s += (
                f"    style.addDrawingStyle(group='Active Layers', name='{prim.name}'"
                ", color=toRGB('White'), pattern=toHexa('antihash0.8'), border=1"
                ", threshold=threshold)\n"
            )
            if hasattr(prim, "pin"):
                for pin in prim.pin:
                    s += (
                        "    style.addDrawingStyle(group='Active Layers'"
                        f", name='{pin.name}', color=toRGB('White')"
                        ", pattern=toHexa('antihash0.8'), border=2"
                        ", threshold=threshold)\n"
                    )
        for i, prim in enumerate(self.tech.primitives.tt_iter_type(prm.GateWire)):
            rgb = "Red" if i == 0 else "Orange"
            s += (
                f"    style.addDrawingStyle(group='Active Layers', name='{prim.name}'"
                f", color=toRGB('{rgb}'), pattern=toHexa('antihash0.8'), border=1"
                ", threshold=threshold)\n"
            )
            if hasattr(prim, "pin"):
                for pin in prim.pin:
                    s += (
                        "    style.addDrawingStyle(group='Active Layers'"
                        f", name='{pin.name}', color=toRGB('{rgb}')"
                        ", pattern=toHexa('antihash0.8'), border=2"
                        ", threshold=threshold)\n"
                    )

        s += "\n    # Routing Layers.\n"
        for i, prim in enumerate(self.tech.primitives.tt_iter_type(prm.MetalWire)):
            rgb = clrs[i%len(clrs)]
            hexa = "slash.8" if i == 0 else "poids4.8"
            s += (
                f"    style.addDrawingStyle(group='Routing Layers', name='{prim.name}'"
                f", color=toRGB('{rgb}'), pattern=toHexa('{hexa}'), border=1"
                ", threshold=threshold)\n"
            )
            if hasattr(prim, "pin"):
                for pin in prim.pin:
                    s += (
                        f"    style.addDrawingStyle(group='Routing Layers'"
                        f", name='{pin.name}', color=toRGB('{rgb}'), pattern=toHexa('{hexa}')"
                        ", border=2, threshold=threshold)\n"
                    )

        s += "\n    # Cuts (VIA holes).\n"
        for i, prim in enumerate(
            self.tech.primitives.tt_iter_type((prm.Via, prm.PadOpening)),
        ):
            rgb = clrs[i%len(clrs)] if i > 0 else "0,150,150"
            s += (
                f"    style.addDrawingStyle(group='Cuts (VIA holes', name='{prim.name}'"
                f", color=toRGB('{rgb}'), threshold=threshold)\n"
            )

        s += "\n    # Blockages.\n"
        blockages = set(prim.blockage for prim in filter(
            lambda p: hasattr(p, "blockage"), self.tech.primitives,
        ))
        for i, prim in enumerate(filter(
            lambda p: p in blockages, self.tech.primitives.tt_iter_type(prm.Marker)
        )):
            rgb = clrs[i%len(clrs)]
            hexa = "slash.8" if i == 0 else "poids4.8"
            s += (
                f"    style.addDrawingStyle(group='Blockages', name='{prim.name}'"
                f", color=toRGB('{rgb}'), pattern=toHexa('{hexa}')"
                ", border=4, threshold=threshold)\n"
            )

        s += indent(dedent("""

            # Knick & Kite.
            style.addDrawingStyle( group='Knik & Kite', name='SPL1'           , color=toRGB('Red'        ) )
            style.addDrawingStyle( group='Knik & Kite', name='AutoLayer'      , color=toRGB('Magenta'    ) )
            style.addDrawingStyle( group='Knik & Kite', name='gmetalh'        , color=toRGB('128,255,200'), pattern=toHexa('antislash2.32'    ), border=1 )
            style.addDrawingStyle( group='Knik & Kite', name='gmetalv'        , color=toRGB('200,200,255'), pattern=toHexa('light_antihash1.8'), border=1 )
            style.addDrawingStyle( group='Knik & Kite', name='gcontact'       , color=toRGB('255,255,190'),                                      border=1 )
            style.addDrawingStyle( group='Knik & Kite', name='Anabatic::Edge' , color=toRGB('255,255,190'), pattern='0000000000000000'         , border=4, threshold=0.02 )
            style.addDrawingStyle( group='Knik & Kite', name='Anabatic::GCell', color=toRGB('255,255,190'), pattern='0000000000000000'         , border=2, threshold=threshold )

            Viewer.Graphics.addStyle( style )
            Viewer.Graphics.setStyle( 'Alliance.Classic [black]' )
        """[1:]), prefix="    ")

        return s


class CoriolisGenerator:
    def __init__(self, tech):
        self.tech = tech

    def __call__(self, obj=None, *, supply="vdd", ground="vss"):
        if obj is None:
            s = self._s_tech()
        elif isinstance(obj, lbr.Library):
            s = self._s_lib(obj, supply=_util.v2t(supply), ground=_util.v2t(ground))
        else:
            raise TypeError("object has to be None or of type 'Library'")

        return s

    def _s_tech(self):
        gen = _TechnologyGenerator()
        return gen(self.tech)

    def _s_lib(self, lib, *, supply, ground):
        gen = _LibraryGenerator(self.tech)
        return gen(lib)
