from . import port as prt, mask as msk

__all__ = ["wafer", "SubstratePort"]

class _Wafer(msk._Mask):
    generated = False

    # Class representing the whole wafer
    def __init__(self):
        if _Wafer.generated:
            raise ValueError("Creating new '_Wafer' object is not allowed. One needs to use wafer.wafer")
        else:
            _Wafer.generated = True
        super().__init__("wafer")

        self.grid = msk._MaskProperty(self, "grid")

    @property
    def designmasks(self):
        return iter(tuple())

wafer = _Wafer()

class SubstratePort(prt.Port):
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)
