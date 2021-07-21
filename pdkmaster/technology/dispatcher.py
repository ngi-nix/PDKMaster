# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from . import primitive as prm


class PrimitiveDispatcher:
    def __call__(self, prim: prm._Primitive, *args, **kwargs):
        classname = prim.__class__.__name__.split(".")[-1]
        return getattr(self, classname, self._pd_unhandled)(prim, *args, **kwargs)

    def _pd_unhandled(self, prim, *args, **kwargs):
        raise RuntimeError(
            "Internal error: unhandled dispatcher for object of type "
            f"{prim.__class__.__name__}"
        )

    def _Primitive(self, prim: prm._Primitive, *args, **kwargs):
        raise NotImplementedError(
            f"No dispatcher implemented for object of type {prim.__class__.__name__}"
        )

    def _MaskPrimitive(self, prim: prm._MaskPrimitive, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)

    def Marker(self, prim: prm.Marker, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def Auxiliary(self, prim: prm.Auxiliary, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)
    
    def _WidthSpacePrimitive(self, prim: prm._WidthSpacePrimitive, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def ExtraProcess(self, prim: prm.ExtraProcess, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Implant(self, prim: prm.Implant, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Well(self, prim: prm.Well, *args, **kwargs):
        return self.Implant(prim, *args, **kwargs)

    def Insulator(self, prim: prm.Insulator, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def _Conductor(self, prim: prm._Conductor, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def WaferWire(self, prim: prm.WaferWire, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def GateWire(self, prim: prm.GateWire, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def MetalWire(self, prim: prm.MetalWire, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def TopMetalWire(self, prim: prm.TopMetalWire, *args, **kwargs):
        return self.MetalWire(prim, *args, **kwargs)
    
    def Via(self, prim, *args: prm.Via, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def PadOpening(self, prim: prm.PadOpening, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def Resistor(self, prim: prm.Resistor, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Diode(self, prim: prm.Diode, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def MOSFETGate(self, prim: prm.MOSFETGate, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def MOSFET(self, prim: prm.MOSFET, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)

    def Spacing(self, prim: prm.Spacing, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)
