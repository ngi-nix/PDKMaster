# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from .. import _util
from . import net as net_, mask as msk

__all__ = ["wafer", "SubstrateNet"]

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

def outside(masks, *, alias=None):
    masks = _util.v2t(masks)
    if len(masks) == 1:
        mask = wafer.remove(masks[0])
    else:
        mask = wafer.remove(msk.Join(set(masks)))
    if alias is None:
        return mask
    else:
        return mask.alias(alias)


class SubstrateNet(net_.Net):
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)

