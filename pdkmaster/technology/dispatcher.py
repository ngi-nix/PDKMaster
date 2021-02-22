# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from . import primitive as prm

class PrimitiveDispatcher:
    def __call__(self, prim, *args, **kwargs):
        if not isinstance(prim, prm._Primitive):
            raise TypeError("prim has to be of type '_Primitive'")
        classname = prim.__class__.__name__.split(".")[-1]
        return getattr(self, classname, self._pd_unhandled)(prim, *args, **kwargs)

    def _pd_unhandled(self, prim, *args, **kwargs):
        raise RuntimeError(
            f"Internal error: unhandled dispatcher for object of type {prim.__class__.__name__}"
        )

    def _Primitive(self, prim, *args, **kwargs):
        raise NotImplementedError(
            f"No dispatcher implemented for object of type {prim.__class__.__name__}"
        )

    def _MaskPrimitive(self, prim, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)

    def Marker(self, prim, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def Auxiliary(self, prim, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)
    
    def _WidthSpacePrimitive(self, prim, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def ExtraProcess(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Implant(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Well(self, prim, *args, **kwargs):
        return self.Implant(prim, *args, **kwargs)

    def Insulator(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def _Conductor(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def WaferWire(self, prim, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def GateWire(self, prim, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def MetalWire(self, prim, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def TopMetalWire(self, prim, *args, **kwargs):
        return self.MetalWire(prim, *args, **kwargs)
    
    def Via(self, prim, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def PadOpening(self, prim, *args, **kwargs):
        return self._Conductor(prim, *args, **kwargs)

    def Resistor(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Diode(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def MOSFETGate(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def MOSFET(self, prim, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)

    def Spacing(self, prim, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)
