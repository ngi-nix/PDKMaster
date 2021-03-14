"""Generate a pdkmaster technology file"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from importlib import import_module
from textwrap import indent, dedent
from logging import warn

from ...technology import dispatcher as dsp, technology_ as tch
from ...design import circuit as ckt, library as lib

__all__ = ["generate"]

def _str_prim(prim):
    return f"prims['{prim.name}']"

def _str_primtuple(t):
    if len(t) == 0:
        return "tuple()"
    elif len(t) == 1:
        return _str_prim(t[0])
    else:
        return f"({', '.join(_str_prim(p) for p in t)})"

def _str_enclosure(enc):
    return f"Enclosure({enc.spec})"

def _str_enclosures(encs):
    if len(encs) == 1:
        return f"({_str_enclosure(encs[0])},)"
    else:
        return f"({','.join(_str_enclosure(enc) for enc in encs)})"

class _PrimitiveGenerator(dsp.PrimitiveDispatcher):
    def _Primitive(self, prim):
        return self._prim_object(prim)

    def Spacing(self, prim):
        return self._prim_object(prim, add_name=False)

    def _prim_object(self, prim, add_name=True):
        class_name = prim.__class__.__name__.split(".")[-1]
        if add_name:
            s_name = f"'{prim.name}'" if add_name else ""
            if hasattr(prim, "mask") and hasattr(prim.mask, "gds_layer"):
                s_name += f", gds_layer={prim.mask.gds_layer}"
        else:
            s_name = ""
        s_param = getattr(self, "_params_"+class_name, self._params_unhandled)(prim)
        if s_param:
            s_param = indent(s_param, prefix="    ")
            if s_name:
                s_name += ","
            return f"prims += {class_name}({s_name}\n{s_param})\n"
        else:
            return f"prims += {class_name}({s_name})\n"

    def _params_unhandled(self, prim):
        raise RuntimeError(f"Internal error: unhandled params for {prim.__class__.__name__}")

    def _params_mask(self, prim, *, add_fill_space=False):
        s = ""
        if hasattr(prim, "grid"):
            s += f"grid={prim.grid},"
        if add_fill_space:
            if s:
                s += " "
            s += f"fill_space='{prim.mask.fill_space}',"
        if hasattr(prim, "blockage"):
            if s:
                s += " "
            s += f"blockage={_str_prim(prim.blockage)},"
        s += "\n"

        return s

    def _params_widthspace(self, prim, *, add_fill_space=False):
        s = f"min_width={prim.min_width}, min_space={prim.min_space},\n"
        if hasattr(prim, "space_table"):
            s += "space_table=(\n"
            for row in prim.space_table:
                s += f"    {row},\n"
            s += "),\n"
        if hasattr(prim, "min_area"):
            s += f"min_area={prim.min_area},\n"
        if hasattr(prim, "min_density"):
            s += f"min_density={prim.min_density},\n"
        if hasattr(prim, "max_density"):
            s += f"max_density={prim.max_density},\n"
        if hasattr(prim, "pin"):
            s += f"pin={_str_primtuple(prim.pin)},\n"
        s += self._params_mask(prim, add_fill_space=add_fill_space)
        
        return s

    def _params_Marker(self, prim):
        return self._params_mask(prim)

    def _params_Auxiliary(self, prim):
        return self._params_mask(prim)

    def _params_ExtraProcess(self, prim):
        return self._params_widthspace(prim, add_fill_space=True)

    def _params_Implant(self, prim):
        s = f"type_='{prim.type_}',\n"
        s += self._params_widthspace(prim)
        return s

    def _params_Well(self, prim):
        if hasattr(prim, "min_space_samenet"):
            s = f"min_space_samenet={prim.min_space_samenet},\n"
        else:
            s = ""
        s += self._params_Implant(prim)
        return s

    def _params_Insulator(self, prim):
        return self._params_widthspace(prim, add_fill_space=True)

    def _params_GateWire(self, prim):
        return self._params_widthspace(prim)

    def _params_MetalWire(self, prim):
        return self._params_widthspace(prim)

    def _params_TopMetalWire(self, prim):
        return self._params_MetalWire(prim)

    def _params_WaferWire(self, prim):
        s = f"allow_in_substrate={prim.allow_in_substrate},\n"
        s += f"implant={_str_primtuple(prim.implant)},\n"
        s += f"min_implant_enclosure={_str_enclosures(prim.min_implant_enclosure)},\n"
        s += f"implant_abut={_str_primtuple(prim.implant_abut)},\n"
        s += f"allow_contactless_implant={prim.allow_contactless_implant},\n"
        s += f"well={_str_primtuple(prim.well)},\n"
        s += "min_well_enclosure="+_str_enclosures(prim.min_well_enclosure)+",\n"
        if hasattr(prim, "min_substrate_enclosure"):
            s += (
                "min_substrate_enclosure="
                f"{_str_enclosure(prim.min_substrate_enclosure)},\n"
            )
        s += f"allow_well_crossing={prim.allow_well_crossing},\n"
        if hasattr(prim, "oxide"):
            s += (
                f"oxide={_str_primtuple(prim.oxide)},\n"
                f"min_oxide_enclosure={_str_enclosures(prim.min_oxide_enclosure)},\n"
            )
        s += self._params_widthspace(prim)
        return s

    def _params_Resistor(self, prim):
        s = f"wire={_str_prim(prim.wire)}, indicator={_str_primtuple(prim.indicator)},\n"
        s += f"min_indicator_extension={prim.min_indicator_extension},\n"
        if hasattr(prim, "contact"):
            assert hasattr(prim, "min_contact_space")
            s += (
                f"contact={_str_prim(prim.contact)},"
                f" min_contact_space={prim.min_contact_space},\n"
            )
        if hasattr(prim, "implant"):
            s += f"implant={_str_prim(prim.implant)}"
            if hasattr(prim, "min_implant_enclosure"):
                s += f", min_implant_enclosure={_str_enclosure(prim.min_implant_enclosure)},\n"
            else:
                s += ",\n"
        if hasattr(prim, "model"):
            s += f"model='{prim.model}', model_params={prim.model_params},\n"
        if hasattr(prim, "sheetres"):
            s += f"sheetres={prim.sheetres},\n"
        s += self._params_widthspace(prim)
        return s

    def _params_Diode(self, prim):
        s = f"wire={_str_prim(prim.wire)}, indicator={_str_primtuple(prim.indicator)},\n"
        s += f"min_indicator_enclosure={_str_enclosures(prim.min_indicator_enclosure)},\n"
        s += f"implant={_str_prim(prim.implant)}"
        if hasattr(prim, "min_implant_enclosure"):
            s += f", min_implant_enclosure={_str_enclosure(prim.min_implant_enclosure)}"
        s += ",\n"
        if hasattr(prim, "well"):
            s += f"well={_str_prim(prim.well)}"
            if hasattr(prim, "min_well_enclosure"):
                s += f", min_well_enclosure={_str_enclosure(prim.min_well_enclosre)}"
            s += ",\n"
        if hasattr(prim, "model"):
            s += f"model='{prim.model}',\n"
        s += self._params_widthspace(prim)
        return s
    
    def _params_Via(self, prim):
        s = f"bottom={_str_primtuple(prim.bottom)},\n"
        s += f"top={_str_primtuple(prim.top)},\n"
        s += f"width={prim.width}, min_space={prim.min_space},\n"
        s += f"min_bottom_enclosure={_str_enclosures(prim.min_bottom_enclosure)},\n"
        s += f"min_top_enclosure={_str_enclosures(prim.min_top_enclosure)},\n"
        s += self._params_mask(prim)
        return s

    def _params_PadOpening(self, prim):
        s = f"bottom={_str_prim(prim.bottom)},\n"
        s += f"min_bottom_enclosure={_str_enclosure(prim.min_bottom_enclosure)},\n"
        s += self._params_widthspace(prim)
        return s

    def _params_Spacing(self, prim):
        s = f"primitives1={_str_primtuple(prim.primitives1)},\n"
        s += f"primitives2={_str_primtuple(prim.primitives2)},\n"
        s += f"min_space={prim.min_space},\n"
        return s

    def _params_MOSFETGate(self, prim):
        s = f"active={_str_prim(prim.active)}, poly={_str_prim(prim.poly)},\n"
        if hasattr(prim, "oxide"):
            s += f"oxide={_str_prim(prim.oxide)},\n"
        if hasattr(prim, "min_gateoxide_enclosure"):
            s += (
                "min_gateoxide_enclosure="
                f"{_str_enclosure(prim.min_gateoxide_enclosure)},\n"
            )
        if hasattr(prim, "inside"):
            s += f"inside={_str_primtuple(prim.inside)},\n"
        if hasattr(prim, "min_gateinside_enclosure"):
            s += (
                "min_gateinside_enclosure="
                f"{_str_enclosures(prim.min_gateinside_enclosure)},\n"
            )
        if hasattr(prim, "min_l"):
            s += f"min_l={prim.min_l},\n"
        if hasattr(prim, "min_w"):
            s += f"min_w={prim.min_w},\n"
        if hasattr(prim, "min_sd_width"):
            s += f"min_sd_width={prim.min_sd_width},\n"
        if hasattr(prim, "min_polyactive_extension"):
            s += f"min_polyactive_extension={prim.min_polyactive_extension},\n"
        if hasattr(prim, "min_gate_space"):
            s += f"min_gate_space={prim.min_gate_space},\n"
        if hasattr(prim, "contact"):
            s += f"contact={_str_prim(prim.contact)}, min_contactgate_space={prim.min_contactgate_space},\n"
        return s

    def _params_MOSFET(self, prim):
        s = f"gate={_str_prim(prim.gate)},\n"
        if hasattr(prim, "implant"):
            s += f"implant={_str_primtuple(prim.implant)},\n"
        if hasattr(prim, "well"):
            s += f"well={_str_prim(prim.well)},\n"
        if hasattr(prim, "min_l"):
            s += f"min_l={prim.min_l},\n"
        if hasattr(prim, "min_w"):
            s += f"min_w={prim.min_w},\n"
        if hasattr(prim, "min_sd_width"):
            s += f"min_sd_width={prim.min_sd_width},\n"
        if hasattr(prim, "min_polyactive_extension"):
            s += f"min_polyactive_extension={prim.min_polyactive_extension},\n"
        s += (
            "min_gateimplant_enclosure="
            f"{_str_enclosures(prim.min_gateimplant_enclosure)},\n"
        )
        if hasattr(prim, "min_gate_space"):
            s += f"min_gate_space={prim.min_gate_space},\n"
        if hasattr(prim, "contact"):
            s += f"contact={_str_prim(prim.contact)}, min_contactgate_space={prim.min_contactgate_space},\n"
        if hasattr(prim, "model"):
            s += f"model='{prim.model}',\n"
        return s

class PDKMasterGenerator:
    def __call__(self, obj):
        if isinstance(obj, tch.Technology):
            return self._gen_tech(obj)
        elif isinstance(obj, ckt._Circuit):
            return self._gen_ckt(obj)
        elif isinstance(obj, lib.Library):
            return self._gen_lib(obj)
        else:
            raise TypeError("obj has to be of type 'Technology' or '_Circuit'")

    def _gen_header(self, tech, cktfab, layoutfab):
        assert (
            isinstance(tech, tch.Technology)
            and isinstance(cktfab, ckt.CircuitFactory)
        ), "Internal error"

        s = "# Autogenerated file. Changes will be overwritten.\n\n"

        mod = tech.__class__.__module__
        mod_split = mod.split(".")
        if mod.startswith("pdkmaster.techs"):
            module = import_module(".".join(mod_split[:3]))
        else:
            module = None

        if module and hasattr(module, "tech") and (tech == module.tech):
            s += f"from {module.__name__} import tech\n"
        else:
            mod_name = type(tech).__module__
            class_name = type(tech).__name__
            s += (
                f"from {mod_name} import {class_name}\n"
                f"tech = {class_name}()\n"
            )

        if cktfab is not None:
            if module and hasattr(module, "cktfab") and (cktfab == module.cktfab):
                s += f"from {module.__name__} import cktfab\n"
            else:
                s += dedent(f"""
                    from pdkmaster.design.circuit import CircuitFactory
                    cktfab = CircuitFactory(tech)
                """[1:])

        if layoutfab is not None:
            if (module and hasattr(module, "layoutfab")
                and (layoutfab == module.layoutfab)
            ):
                s += f"from {module.__name__} import layoutfab\n"
            else:
                s += dedent(f"""
                    from pdkmaster.design.layout import LayoutFactory
                    layoutfab = LayoutFactory(tech)
                """[1:])

        s += "\n"

        return s

    def _gen_tech(self, tech):
        s = dedent(f"""
            # Autogenerated file. Changes will be overwritten.

            from pdkmaster.technology.primitive import *
            from pdkmaster.technology.property_ import Enclosure
            from pdkmaster.technology.technology_ import Technology
            from pdkmaster.design.layout import LayoutFactory
            from pdkmaster.design.circuit import CircuitFactory
            
            __all__ = [
                "technology", "tech",
                "layoutfab", "layout_factory",
                "cktfab", "circuit_factory",
            ]

            class {tech.name}(Technology):
                name = "{tech.name}"
                grid = {tech.grid}
                substrate_type = "{tech.substrate_type}"
            
                def _init(self):
                    prims = self._primitives
            
        """[1:])
        gen = _PrimitiveGenerator()
        s += indent(
            "".join(gen(prim) for prim in tech.primitives),
            prefix="        "
        )
        s += dedent(f"""

            technology = tech = {tech.name}()
            cktfab = circuit_factory = CircuitFactory(tech)
            layoutfab = layout_factory = LayoutFactory(tech)
        """[1:])

        return s

    def _gen_ckt(self, circuit, *, lib=None, header=True):
        s = ""
        if header:
            s += self._gen_header(circuit.fab.tech, circuit.fab, None)

            s += dedent(f"""
                __all__ ["circuit", "ckt"]

                circuit = ckt = cktfab.new_circuit("{circuit.name}")

            """)

        for net in circuit.nets:
            external = net in circuit.ports
            s += f"ckt.new_net('{net.name}', external={external})\n"
        s += "\n"

        for inst in circuit.instances:
            if isinstance(inst, ckt._PrimitiveInstance):
                primname = inst.prim.name
                s += f"ckt.new_instance('{inst.name}', tech.primitives['{primname}'],\n"
                for param in inst.prim.params:
                    s += f"    {param.name}={inst.params[param.name]!r},\n"
                s += ")\n"
            elif isinstance(inst, ckt._CellInstance):
                if lib is None:
                    raise ValueError(
                        "Can't export single Circuit with Cell instances outside library export"
                    )
                elif inst.cell not in lib.cells:
                    raise ValueError(
                        "Can't export Circuit with inter-library cell instance(s)"
                    )

                cellname = inst.cell.name
                s += f"ckt.new_instance('{inst.name}', self.cells['{cellname}'].circuit"
                if hasattr(inst, "circuitname"):
                    s += f", circuitname={inst.circuitname}"
                s += ")\n"
            else:
                raise AssertionError("Internal error: unsupported instance class")

        s += "\n"

        for net in circuit.nets:
            s += f"ckt.nets['{net.name}'].childports += (\n"
            for port in net.childports:
                inst = port.inst
                s += (
                    f"    ckt.instances['{inst.name}'].ports['{port.name}'],\n"
                )
            s += ")\n"

        return s

    def _gen_lib(self, library, header=True):
        s = ""
        if header:
            s += dedent("""
                # Autogenerated file. Changes will be overwritten.

                from pdkmaster.design.library import Library
                from pdkmaster.technology.property_ import Enclosure

            """[1:])

            s += self._gen_header(library.tech, library.cktfab, library.layoutfab)

            s += dedent("""
                __all__ = ["library", "lib"]

                library = lib = Library(tech, cktfab, layoutfab)
            """)

        for cell in library.sorted_cells:
            s += dedent(f"""

                # cell: {cell.name}
                cell = lib.new_cell('{cell.name}')
            """)
            for circuit in cell.circuits:
                s += f"ckt = cell.new_circuit('{circuit.name}')\n"
                s += self._gen_ckt(circuit, lib=library, header=False)

        # if cell.layouts:
        #     raise NotImplementedError("Library cells export with layout")

        return s

generate = PDKMasterGenerator()
