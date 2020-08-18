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

    def Implant(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Well(self, prim, *args, **kwargs):
        return self.Implant(prim, *args, **kwargs)

    def Deposition(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Wire(self, prim, *args, **kwargs):
        return self.Deposition(prim, *args, **kwargs)

    def BottomWire(self, prim, *args, **kwargs):
        return self.Wire(prim, *args, **kwargs)

    def TopWire(self, prim, *args, **kwargs):
        return self.Wire(prim, *args, **kwargs)

    def WaferWire(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def DerivedWire(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)
    
    def Via(self, prim, *args, **kwargs):
        return self._MaskPrimitive(prim, *args, **kwargs)

    def PadOpening(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def Spacing(self, prim, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)

    def MOSFETGate(self, prim, *args, **kwargs):
        return self._WidthSpacePrimitive(prim, *args, **kwargs)

    def MOSFET(self, prim, *args, **kwargs):
        return self._Primitive(prim, *args, **kwargs)
