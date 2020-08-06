from . import mask as msk

__all__ = ["wafer"]

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

wafer = _Wafer()
