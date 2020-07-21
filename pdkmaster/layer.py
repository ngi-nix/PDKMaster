from . import condition as cond, property_ as prop

__all__ = ["Layer", "Layers"]

class _LayerProperty(prop.Property):
    def __init__(self, layer, name):
        assert (isinstance(layer, Layer) and isinstance(name, str)), "Internal error"

        super().__init__(layer.name + "." + name)
        self.layer = layer
        self.prop_name = name

class _DualLayerProperty(prop.Property):
    def __init__(self, layer1, layer2, name, *, commutative):
        assert (
            isinstance(layer1, Layer) and isinstance(layer2, Layer)
            and isinstance(name, str) and isinstance(commutative, bool)
        ), "Internal error"

        name = "{}.{}.{}".format(layer1.name, layer2.name, name)
        if commutative:
            alias = "{}.{}.{}".format(layer2.name, layer1.name, name)
            super().__init__(name, alias)
        else:
            super().__init__(name)

        self.layer1 = layer1
        self.layer2 = layer2
        self.prop_name = name

class _LayerMultiCondition(cond.Condition):
    def __init__(self, layer, others):
        assert (isinstance(layer, Layer) and len(others) != 0), "Internal error"
        super().__init__((layer, others))

        self.layer = layer
        self.others = others

    def __hash__(self):
        return hash((self.layer, self.others))

class _InsideCondition(_LayerMultiCondition):
    pass
class _OutsideCondition(_LayerMultiCondition):
    pass

class Layer:
    def __init__(self, name):
        self.name = name
        self.width = _LayerProperty(self, "width")
        self.space = _LayerProperty(self, "space")
        self.grid = _LayerProperty(self, "grid")

    def space_to(self, other):
        if not isinstance(other, Layer):
            raise TypeError("other has to be of type 'Layer'")

        return _DualLayerProperty(self, other, "space", commutative=True)

    def extend_over(self, other):
        if not isinstance(other, Layer):
            raise TypeError("other has to be of type 'Layer'")

        return _DualLayerProperty(self, other, "extend_over", commutative=False)

    def enclosed_by(self, other):
        if not isinstance(other, Layer):
            raise TypeError("other has to be of type 'Layer'")

        return _DualLayerProperty(self, other, "enclosed_by", commutative=False)

    def overlap_with(self, other):
        if not isinstance(other, Layer):
            raise TypeError("other has to be of type 'Layer'")

        return _DualLayerProperty(self, other, "overlap_with", commutative=True)

    def is_inside(self, other, *others):
        if isinstance(other, Layer):
            layers = (other, *others)
        else:
            try:
                layers = (*other, *others)
            except:
                raise TypeError("Outside layer not of type 'Layer'")
        for l in layers:
            if not isinstance(l, Layer):
                raise TypeError("Outside layer not of type 'Layer'")
        
        return _InsideCondition(self, layers)

    def is_outside(self, other, *others):
        if isinstance(other, Layer):
            layers = (other, *others)
        else:
            try:
                layers = (*other, *others)
            except:
                raise TypeError("Outside layer not of type 'Layer'")
        for l in layers:
            if not isinstance(l, Layer):
                raise TypeError("Outside layer not of type 'Layer'")
        
        return _OutsideCondition(self, layers)

class Layers:
    def __init__(self):
        self._layers = {}

    def __getitem__(self, key):
        return self._layers[key]

    def __getattr__(self, name):
        return self._layers[name]

    def __iadd__(self, other):
        e = TypeError("Can only add 'Layer' object or an iterable of 'Layer' objects to 'Layers'")
        try:
            for layer in other:
                if not isinstance(layer, Layer):
                    raise e
        except TypeError:
            if not isinstance(other, Layer):
                raise e
            other = (other,)
        for layer in other:
            if layer.name in self._layers:
                raise ValueError("Layer '{}' already exists".format(layer.name))
        self._layers.update({layer.name: layer for layer in other})
        
        return self