from . import property_ as prop, condition as cond, layer, device as dev

__all__ = ["Technology"]

class Technology:
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("name has to be a string")

        self.name = name
        self.grid = prop.Property(name + ".grid")
        self._constraints = cond.Conditions()
        self._layers = layers = layer.Layers()
        self._devices = dev.Devices()

        layers += layer.Layer("wafer")

    @property
    def constraints(self):
        return self._constraints
    @constraints.setter
    def constraints(self, v):
        if v != self._constraints:
            raise AttributeError("You can update constraints attribute only with '+=' operator")

    @property
    def layers(self):
        return self._layers
    @layers.setter
    def layers(self, v):
        if v != self._layers:
            raise AttributeError("You can update constraints attribute only with '+=' operator")

    @property
    def devices(self):
        return self._devices
    @devices.setter
    def devices(self, v):
        if v != self._devices:
            raise AttributeError("You can update devices attribute only with '+=' operator")

