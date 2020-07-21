"""The native technology devices"""

from . import property_ as prop, layer

__all__ = ["Interconnect", "MOSFET"]

class _Device:
    def __init__(self, name):
        if not isinstance(name, str):
            raise RuntimeError("Internal Error: name is not a string")
        
        self.name = name

class _DeviceProperty(prop.Property):
    def __init__(self, name, device, *, type_=float):
        super().__init__(name, type_=type_)
        if not isinstance(device, _Device):
            raise RuntimeError("Internal error: device not of type 'Device'")

class Interconnect(_Device):
    def __init__(self, lay, *, name=None):
        if not isinstance(lay, layer.Layer):
            raise TypeError("layer is not of type 'Layer'")
        if name is None:
            name = lay.name + "_interconnect"
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)

        self.layer = lay

class MOSFET(_Device):
    def __init__(
        self, name, *,
        poly, active, implant, well=None,
        model=None,
    ):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")
        super().__init__(name)
        if not isinstance(poly, layer.Layer):
            raise TypeError("poly has to of type 'Layer'")
        if not isinstance(active, layer.Layer):
            raise TypeError("active has to of type 'Layer'")
        ok = True
        try:
            for l in implant:
                if not isinstance(l, layer.Layer):
                    ok = False
                    break
        except:
            ok = isinstance(implant, layer.Layer)
        if not ok:
            raise TypeError("implant has to be of type 'Layer' or an iterable of type 'Layer'")
        if well is not None:
            ok = True
            try:
                for l in well:
                    if not isinstance(l, layer.Layer):
                        ok = False
                        break
            except:
                ok = isinstance(well, layer.Layer)
            if not ok:
                raise TypeError("well has to be of type 'Layer' or an iterable of type 'Layer'")
        if model is None:
            model = name
    
        self.poly = poly
        self.active = active
        self.implant = implant
        self.well = well
        self.gate = layer.Layer(name + ".gate")
        self.model = model

        self.l = prop.Property(name + ".l")
        self.w = prop.Property(name + ".w")

class Devices:
    def __init__(self):
        self._devices = {}

    def __getitem__(self, key):
        return self._devices[key]

    def __getattr__(self, name):
        return self._devices[name]

    def __iadd__(self, other):
        e = TypeError("Can only add 'Device' object or an iterable of 'Device' objects to 'Devices'")
        try:
            for device in other:
                if not isinstance(device, _Device):
                    raise e
        except TypeError:
            if not isinstance(device, _Device):
                raise e
            other = (other,)
        for device in other:
            if device.name in self._devices:
                raise ValueError("Device '{}' already exists".format(device.name))
        self._devices.update({device.name: device for device in other})

        return self