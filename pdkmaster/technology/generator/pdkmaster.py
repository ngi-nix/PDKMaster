"""Generate a pdkmaster technology file"""
from textwrap import indent
from logging import warn

from .. import dispatcher as dsp, technology_ as tch

__all__ = ["PDKMasterGenerator"]


def _str_prim(prim):
    return f"prims['{prim.name}']"

def _str_primtuple(t):
    if len(t) == 0:
        return "tuple()"
    elif len(t) == 1:
        return _str_prim(t[0])
    else:
        return f"({', '.join(_str_prim(p) for p in t)})"

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

    def _params_mask(self, prim):
        s = ""
        if hasattr(prim, "grid"):
            s += f"grid={prim.grid},\n"
        return s

    def _params_widthspace(self, prim):
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
        s += self._params_mask(prim)
        
        return s

    def _params_Marker(self, prim):
        return self._params_mask(prim)

    def _params_Auxiliary(self, prim):
        return self._params_mask(prim)

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

    def _params_Deposition(self, prim):
        return self._params_widthspace(prim)

    def _params_Wire(self, prim):
        return self._params_Deposition(prim)

    def _params_BottomWire(self, prim):
        return self._params_Wire(prim)

    def _params_TopWire(self, prim):
        return self._params_Wire(prim)

    def _params_WaferWire(self, prim):
        s = f"allow_in_substrate={prim.allow_in_substrate},\n"
        s += f"implant={_str_primtuple(prim.implant)},\n"
        s += f"implant_abut={_str_primtuple(prim.implant_abut)},\n"
        s += f"allow_contactless_implant={prim.allow_contactless_implant},\n"
        s += f"well={_str_primtuple(prim.well)},\n"
        s += f"min_well_enclosure={prim.min_well_enclosure},\n"
        if hasattr(prim, "min_substrate_enclosure"):
            s += f"min_substrate_enclosure={prim.min_substrate_enclosure},\n"
        s += f"allow_well_crossing={prim.allow_well_crossing},\n"
        s += self._params_widthspace(prim)
        return s

    def _params_DerivedWire(self, prim):
        s = f"wire={_str_prim(prim.wire)}, marker={_str_primtuple(prim.marker)},\n"
        s += f"min_enclosure={prim.min_enclosure},\n"
        s += self._params_widthspace(prim)
        return s
    
    def _params_Via(self, prim):
        s = f"bottom={_str_primtuple(prim.bottom)},\n"
        s += f"top={_str_primtuple(prim.top)},\n"
        s += f"width={prim.width}, min_space={prim.min_space},\n"
        bottom_enc = (
            prim.min_bottom_enclosure
            if len(prim.bottom) != 1
            else prim.min_bottom_enclosure[0]
        )
        top_enc = (
            prim.min_top_enclosure
            if len(prim.top) != 1
            else prim.min_top_enclosure[0]
        )
        s += f"min_bottom_enclosure={bottom_enc}, min_top_enclosure={top_enc},\n"
        s += self._params_mask(prim)
        return s

    def _params_PadOpening(self, prim):
        s = f"bottom={_str_prim(prim.bottom)}, min_bottom_enclosure={prim.min_bottom_enclosure},\n"
        s += self._params_widthspace(prim)
        return s

    def _params_Spacing(self, prim):
        s = f"primitives1={_str_primtuple(prim.primitives1)},\n"
        s += f"primitives2={_str_primtuple(prim.primitives2)},\n"
        s += f"min_space={prim.min_space},\n"
        return s

    def _params_MOSFETGate(self, prim):
        s = f"poly={_str_prim(prim.poly)}, active={_str_prim(prim.active)},\n"
        if hasattr(prim, "oxide"):
            s += f"oxide={_str_prim(prim.oxide)},\n"
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
        s += f"min_gateimplant_enclosure={prim.min_gateimplant_enclosure},\n"
        if hasattr(prim, "min_gate_space"):
            s += f"min_gate_space={prim.min_gate_space},\n"
        if hasattr(prim, "contact"):
            s += f"contact={_str_prim(prim.contact)}, min_contactgate_space={prim.min_contactgate_space},\n"
        if hasattr(prim, "model"):
            s += f"model='{prim.model}',\n"
        return s

class PDKMasterGenerator:
    def __call__(self, tech):
        if not isinstance(tech, tch.Technology):
            raise TypeError("PDKMasterGenerator has to be called with tech as parameter")
        s = "from pdkmaster.technology.primitive import *\n"
        s += "from pdkmaster.technology.technology_ import Technology\n"
        s += "\n"
        s += f"class {tech.name}(Technology):\n"
        s += f"    name = '{tech.name}'\n"
        s += f"    grid = {tech.grid}\n"
        s += f"    substrate_type = '{tech.substrate_type}'\n"
        s += "\n"
        s += "    def _init(self):\n"
        s += "        prims = self._primitives\n"
        s += "\n"
        gen = _PrimitiveGenerator()
        s += indent(
            "".join(gen(prim) for prim in tech.primitives),
            prefix="        "
        )
        s += "\n"
        s += f"technology = tech = {tech.name}()"
        return s