import re
from collections import OrderedDict

from modgrammar import *

grammar_whitespace_mode = "optional"
# Include comments in whitespace
grammar_whitespace = re.compile(r'(\s+|;.*?\n)+')

_debug = False
#_debug = True

#
# Text conversion helper functions
#
def _strip_string(v, *, allow_nonstring=False):
    if isinstance(v, str):
        if v[0] == '"':
            return v[1:-1]
        elif v[0] == "'":
            return v[1:]
    elif not allow_nonstring:
        raise ValueError("'{}' is not a string".format(v))
    return v

def _get_layername(v):
    if isinstance(v, str):
        return _strip_string(v)
    else:
        return _strip_string(v[0])+"."+_strip_string(v[1])

def _get_layerpairname(v):
    return _get_layername(v[0]) + ":" + _get_layername(v[1])

def _get_bool(v, *, allow_nonbool=False):
    if isinstance(v, str):
        s = _strip_string(v)
        if s == "t":
            return True
        elif s == 'nil':
            return False
    if not allow_nonbool:
        raise ValueError("Error converting '{}' to bool".format(v))
    return v

def _get_numornil(v):
    if isinstance(v, str):
        assert v == "nil"
        return None
    else:
        assert isinstance(v, (int, float))
        return v


#
# Data building helper functions for the NamedList
#
def _build_simple(elems, **kwargs):
    return elems

def _build_techParams(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) == 2
        paramname = _strip_string(v[0])
        if paramname.endswith("layer") | paramname.endswith("Layer"):
            ret[paramname] = _get_layername(v[1])
        elif paramname.endswith("layers"):
            if not isinstance(v[1], str):
                ret[paramname] = [_get_layername(layer) for layer in v[1]]
            else:
                assert _strip_string(v[1]) == "nil"
        else:
            ret[v[0]] = _strip_string(v[1], allow_nonstring=True)

    return ret

def _build_name_abbreviation(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) in (2, 3)
        techname = _strip_string(v[0])
        d = {"number": v[1]}
        if len(v) > 2:
            d["abbreviation"] = v[2]
        ret[techname] = d

    return ret

def _build_layer_purpose(elems, **kwargs):
    ret = []
    for v in elems:
        assert len(v) == 2
        ret.append(_get_layername(v))

    return ret

def _build_techDisplays(elems, **kwargs):
    ret = {}
    for v in elems:
        layername = _get_layername(v[0:2])
        ret[layername] = {
            "packet": v[2],
            "visible": _get_bool(v[3]),
            "selectable": _get_bool(v[4]),
            "con2chgly": _get_bool(v[5]),
            "drawable": _get_bool(v[6]),
            "valid": _get_bool(v[7]),
        }

    return ret

def _build_standardViaDefs(elems, **kwargs):
    ret = []
    for v in elems:
        d = {
            "name": v[0],
            "layer1": {
                "name": _get_layername(v[1]),
                "enclosure": v[5],
                "offset": v[7],
            },
            "via": {
                "name": _get_layername(v[3][0]),
                "width": v[3][1],
                "height": v[3][2],
                "rows": v[4][0],
                "cols": v[4][1],
            },
            "layer2": {
                "name": _get_layername(v[2]),
                "enclosure": v[6],
                "offset": v[8],
            },
            "offset": v[9],
        }
        if len(v[3]) > 3:
            d["via"]["resistance"] = v[3][3]
        if len(v[4]) > 2:
            d["via"]["space"] = v[4][2]
        if len(v[4]) > 3:
            d["via"]["pattern"] = v[4][3]
        if len(v) > 10:
            d["layer1"]["implant"] = {
                "name": _get_layername(v[10]),
                "enclosure": v[11],
            }
        if len(v) > 12:
            d["layer2"]["implant"] = {
                "name": _get_layername(v[12]),
                "enclosure": v[13],
            }
            if len(v) > 14:
                d["well"] = v[14]

        ret.append(d)

    return ret

def _build_customViaDefs(elems, **kwargs):
    ret = {}
    for v in elems:
        vianame = _strip_string(v[0])
        assert vianame not in ret
        ret[vianame] ={
            "library": _strip_string(v[1]),
            "cell": _strip_string(v[2]),
            "view": _strip_string(v[3]),
            "layer1": _get_layername(v[4]),
            "layer2": _get_layername(v[5]),
            "resistance": v[6],
        }

    return ret

def _build_prop_value(elems, **kwargs):
    ret = {}
    for v in elems:
        assert 2 <= len(v) <= 4
        prop = _strip_string(v[0])
        value = _strip_string(v[1], allow_nonstring=True)
        ret[prop] = value
        if len(v) > 2:
            prop += "."+_strip_string(v[2])
            value = _strip_string(v[3], allow_nonstring=True) if len(v) > 3 else True
            ret[prop] = value

    return ret

def _build_layer_value(elems, *, unique=False, **kwargs):
    ret = {}
    for layer, value in elems:
        layername = _get_layername(layer)
        if unique:
            assert layername not in ret
        ret[layername] = _strip_string(value, allow_nonstring=True)

    return ret

def _build_layer_list(elems, **kwargs):
    ret = {}
    for v in elems:
        ret[_get_layername(v[0])] = [_strip_string(value, allow_nonstring=True) for value in v[1:]]

    return ret

def _build_layers_via(elems, **kwargs):
    ret = {}
    for layer1, via, layer2 in elems:
        layerpair = _get_layerpairname((layer1, layer2))
        ret[layerpair] = _get_layername(via)

    return ret

def _build_prop_value_units(elems, **kwargs):
    ret = {}
    for layer, units, value in elems:
        ret[_strip_string(layer)] = [_strip_string(value, allow_nonstring=True), _strip_string(units)]

    return ret

def _build_prop_layers_value_optextra(elems, **kwargs):
    """data: [prop (layer1 (layer2 (layer3))) value (extraprop (extravalue))]
    if no layer is present "_" will be used for layername"""
    ret = {}
    for v in elems:
        cond = _strip_string(v[0])
        if len(v) == 2:
            layer = "_"
            spec = v[1]
            extra = None
        elif (type(v[2]) is str) or ((type(v[2]) is list) and (type(v[2][0]) is str)):
            layer = _get_layerpairname(v[1:3])
            spec = v[3]
            another_layer = (
                ((type(spec) is str) and spec not in ("t", "nil"))
                or ((type(spec) is list) and (type(spec[0]) is str))
            )
            if another_layer:
                layer = _get_layerpairname([layer, v[3]])
                spec = v[4]
                if len(v) > 5:
                    extra = cond + "." + _strip_string(v[5])
                    extra_spec = _strip_string(v[6], allow_nonstring=True) if len(v) > 6 else True
                else:
                    extra = None
            else:
                if len(v) > 4:
                    extra = cond + "." + _strip_string(v[4])
                    extra_spec = _strip_string(v[5], allow_nonstring=True) if len(v) > 5 else True
                else:
                    extra = None
        else:
            layer = _get_layername(v[1])
            spec = v[2]
            if len(v) > 3:
                extra = cond + "." + _strip_string(v[3])
                extra_spec = _strip_string(v[4], allow_nonstring=True) if len(v) > 4 else True
            else:
                extra = None
        spec = _get_bool(spec, allow_nonbool=True)
        if layer in ret:
            ret[layer][cond] = spec
        else:
            ret[layer] = {cond: spec}
        if extra:
            ret[layer][extra] = extra_spec

    return ret

def _build_prop_cumulative_value(elems, *, listname, **kwargs):
    d = {}
    for v in elems:
        cond = _strip_string(v[0])
        if listname == "cumulativeMetalAntenna":
            cond += ".cumulative_metal"
        elif listname == "cumulativeViaAntenna":
            cond += ".cumulative_via"
        else:
            raise Exception("unhandled name '{}'".format(name))
        d[cond] = v[1]
        if len(v) > 2:
            d[cond + "." + _strip_string(v[2])] = True if len(v) == 3 else _strip_string(v[3], allow_nonstring=True)

    return {"_": d}

def _build_spacingTables(elems, **kwargs):
    ret = {}
    for v in elems:
        if isinstance(v[2], list):
            layer = _get_layername(v[1])
            define = v[2]
            table = v[3]
            tail = v[4:]
        elif len(v) > 4:
            layer = _get_layerpairname(v[1:3])
            define = v[3]
            table = v[4]
            tail = v[5:]
        else:
            raise ValueError("Unexpected spacingTables length")
        assert len(define[0]) == 3 or len(define[0]) == 6
        assert define[0][1] == "nil" and define[0][2] == "nil"

        d = {
            "index": _strip_string(define[0][0]),
        }

        if len(define[0]) > 3:
            assert define[0][4] == "nil" and define[0][5] == "nil"
            d["index2"] = _strip_string(define[0][3])
        if len(define) > 1:
            d["default"] = define[1]
        if len(define[0]) == 3:
            d["table"] = [[table[2*i], table[2*i+1]] for i in range(len(table)//2)]
        else: # len(define[0]) == 6
            d["table"] = [[*table[2*i], table[2*i+1]] for i in range(len(table)//2)]

        if len(tail) == 1:
            d[_strip_string(tail[0])] = True
        elif len(tail) > 1:
            d[_strip_string(tail[0])] = tail[1]

        if layer in ret:
            ret[layer][v[0]] = d
        else:
            ret[layer] = {v[0]: d}

    return ret

def _build_viaSpecs(elems, **kwargs):
    ret = {}
    for v in elems:
        layer = _get_layerpairname(v[0:2])
        if len(v[2]) == 1:
            vias = _strip_string(v[2][0])
        else:
            vias = [_strip_string(via) for via in v[2]]
        ret[layer] = vias
    
    return ret

def _build_antennaModels(elems, **kwargs):
    ret = {}
    for v in elems:
        modelname = _strip_string(v[0])
        rules = {}
        for rule in v[1:]:
            for rulename, spec in rule.items():
                assert rulename in (
                    "antenna", "cumulativeMetalAntenna", "cumulativeViaAntenna",
                )
                for layer, layerspec in spec.items():
                    if layer in rules:
                        rules[layer].update(layerspec)
                    else:
                        rules[layer] = layerspec
        ret[modelname] = rules

    return ret

def _build_constraintGroups(elems, **kwargs):
    ret = {}
    for v in elems:
        groupname = _strip_string(v[0])
        override = _get_bool(v[1])
        constraints = {"override": override}
        if (len(v) > 2) and isinstance(v[2], str):
            constraints["abbreviation"] = _strip_string(v[2])
            start = 3
        else:
            start = 2
        for constraint in v[start:]:
            constraints.update(constraint)
        ret[groupname] = constraints

    return ret

def _build_techDerivedLayers(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) == 3 and len(v[2]) == 3
        if isinstance(v[2][2], (int, float)):
            ret[_strip_string(v[0])] = {
                "number": v[1],
                "layer": _get_layername(v[2][0]),
                _strip_string(v[2][1]): v[2][2],
            }
        else:
            ret[_strip_string(v[0])] = {
                "number": v[1],
                "layer": _get_layerpairname([v[2][0], v[2][2]]),
                "operation": _strip_string(v[2][1]),
            }

    return ret

def _build_equivalentLayers(elems, **kwargs):
    ret = {}
    for layer1, layer2 in elems:
        ret[_get_layername(layer1)] = _get_layername(layer2)

    return ret

def _build_functions(elems, **kwargs):
    ret = {}
    for v in elems:
        assert 2 <= len(v) <= 3
        layer = _get_layername(v[0])
        assert layer not in ret
        ret[layer] = {"function": _strip_string(v[1])}
        if len(v) > 2:
            ret[layer]["mask_number"] = v[2]

    return ret

def _build_multipartPathTemplates(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) == 5
        
        pathname = _strip_string(v[0])

        v2 = v[1]
        l = len(v2)
        assert 1 <= l <= 9
        d = {"layer": _get_layername(v2[0])}
        if l > 1:
            d["width"] = v2[1]
        if l > 2:
            d["choppable"] = _get_bool(v2[2])
        if l > 3:
            d["endtype"] = _strip_string(v2[3])
        if l > 4:
            d["begin_extension"] = v2[4]
        if l > 5:
            d["end_extension"] = v2[5]
        if l > 6:
            d["justify"] = _get_bool(v2[6])
        if l > 7:
            d["offset"] = v2[7]
        if l > 8:
            d["connectivity"] = v2[8]
        spec = {"master": d}

        v2 = v[2]
        if not isinstance(v2, str):
            subpaths = []
            for v3 in v2:
                l = len(v3)
                assert 1 <= l <= 8
                d = {"layer": _get_layername(v3[0])}
                if l > 1:
                    d["width"] = v3[1]
                if l > 2:
                    d["choppable"] = _get_bool(v3[2])
                if l > 3:
                    d["separation"] = v3[3]
                if l > 4:
                    d["justification"] = _strip_string(v3[4])
                if l > 5:
                    d["begin_offset"] = v3[5]
                if l > 6:
                    d["end_offset"] = v3[6]
                if l > 7:
                    d["connectivity"] = v3[7]
                subpaths.append(d)
                spec["offset"] = subpaths
        else:
            assert _strip_string(v2) == "nil"

        v2 = v[3]
        if not isinstance(v2, str):
            subpaths = []
            for v3 in v2:
                l = len(v3)
                assert 1 <= l <= 7
                d = {"layer": _get_layername(v3[0])}
                if l > 1:
                    d["enclosure"] = v3[1]
                if l > 2:
                    d["choppable"] = _get_bool(v3[2])
                if l > 3:
                    d["separation"] = v3[3]
                if l > 4:
                    d["begin_offset"] = v3[4]
                if l > 5:
                    d["end_offset"] = v3[5]
                if l > 6:
                    d["connectivity"] = v3[6]
                subpaths.append(d)
            spec["enclosure"] = subpaths
        else:
            assert _strip_string(v2) == "nil"

        v2 = v[4]
        if not isinstance(v2, str):
            subpaths = []
            for v3 in v2:
                l = len(v3)
                assert 1 <= l <= 13
                d = {"layer": _get_layername(v3[0])}
                if l > 1:
                    n = _get_numornil(v3[1])
                    if n is not None:
                        d["width"] = n
                if l > 2:
                    n = _get_numornil(v3[2])
                    if n is not None:
                        d["length"] = n
                if l > 3:
                    d["choppable"] = _get_bool(v3[3])
                if l > 4:
                    d["separation"] = v3[4]
                if l > 5:
                    d["justification"] = _strip_string(v3[5])
                if l > 6:
                    n = _get_numornil(v3[6])
                    if n is not None:
                        d["space"] = n
                if l > 7:
                    d["begin_offset"] = v3[7]
                if l > 8:
                    d["end_offset"] = v3[8]
                if l > 9:
                    d["gap"] = _strip_string(v3[9])
                if l > 10:
                    c = v3[10]
                    if not (isinstance(c, str) and c == "nil"):
                        d["connectivity"] = c
                if l > 11:
                    n = _get_numornil(v3[11])
                    if n is not None:
                        d["begin_segoffset"] = n
                if l > 12:
                    n = _get_numornil(v3[12])
                    if n is not None:
                        d["end_segoffset"] = n
                subpaths.append(d)
            spec["rects"] = subpaths

        ret[pathname] = spec

    return ret

def _build_streamLayers(elems, **kwargs):
    ret = {}
    for layer, number, datatype, translate in elems:
        layername = _get_layername(layer)
        ret[layername] = {
            "number": number,
            "datatype": datatype,
            "translate": _get_bool(translate),
        }

    return ret

def _build_layerFunctions(elems, **kwargs):
    ret = {}
    for v in elems:
        assert 2 <= len(v) <= 3
        layername = _get_layername(v[0])
        d = {"function": _strip_string(v[1])}
        if len(v) > 2:
            d["masknumber"] = v[2]
        assert layername not in ret
        ret[layername] = d

    return ret

def _build_spacingRules(elems, **kwargs):
    ret = {}
    for v in elems:
        specname = _strip_string(v[0])
        assert 3 <= len(v) <= 4
        if len(v) == 3:
            layername = _get_layername(v[1])
        elif len(v) == 4:
            layername = _get_layerpairname(v[1:3])
        specvalue = v[-1]
        if layername in ret:
            ret[layername][specname] = specvalue
        else:
            ret[layername] = {specname: specvalue}

    return ret

_build_NamedList = {
    "techParams": _build_techParams,
    "techPurposes": _build_name_abbreviation,
    "techLayers": _build_name_abbreviation,
    "techLayerPurposePriorities": _build_layer_purpose,
    "techDisplays": _build_techDisplays,
    "standardViaDefs": _build_standardViaDefs,
    "customViaDefs": _build_customViaDefs,
    "interconnect": _build_prop_value,
    "routingGrids": _build_prop_layers_value_optextra,
    "spacings": _build_prop_layers_value_optextra,
    "orderedSpacings": _build_prop_layers_value_optextra,
    "electrical": _build_prop_layers_value_optextra,
    "orderedElectrical": _build_prop_layers_value_optextra,
    "antenna": _build_prop_layers_value_optextra,
    "techLayerProperties": _build_prop_layers_value_optextra,
    "characterizationRules": _build_prop_layers_value_optextra,
    "currentDensity": _build_prop_layers_value_optextra,
    "cumulativeMetalAntenna": _build_prop_cumulative_value,
    "cumulativeViaAntenna": _build_prop_cumulative_value,
    "spacingTables": _build_spacingTables,
    "viaSpecs": _build_viaSpecs,
    "antennaModels": _build_antennaModels,
    "constraintGroups": _build_constraintGroups,
    "viewTypeUnits": _build_prop_value_units,
    "techDerivedLayers": _build_techDerivedLayers,
    "equivalentLayers": _build_equivalentLayers,
    "functions": _build_functions,
    "routingDirections": _build_layer_value,
    "stampLabelLayers": _build_layer_list,
    "multipartPathTemplates": _build_multipartPathTemplates,
    "viaLayers": _build_layers_via,
    "streamLayers": _build_streamLayers,
    "layerFunctions": _build_layerFunctions,
    "spacingRules": _build_spacingRules,
    "orderedSpacingRules": _build_spacingRules,
    "compactorLayers": (_build_layer_value, {"unique": True})
}


class MyGrammar(Grammar):
    def __init__(self, *args):
        super().__init__(*args)
        if _debug:
            print("{}: {}-{}".format(self.__class__.__name__, args[1], args[2]))

class Identifier(MyGrammar):
    # Identifier can start with ' for LISP symbol
    grammar = WORD("'a-zA-Z_?", "a-zA-Z0-9_?")

    def grammar_elem_init(self, sessiondata):
        self.value = self.string

class Number(MyGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = (
        OPTIONAL(L("-")|L("+")), WORD("0-9."),
        OPTIONAL(L("e"), OPTIONAL(L("-")|L("+")), WORD("0-9")),
    )

    def grammar_elem_init(self, sessiondata):
        isfloat = ("." in self.string) or ("e" in self.string)
        self.value = float(self.string) if isfloat else int(self.string)

class String(MyGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = (L('"'), ZERO_OR_MORE(ANY_EXCEPT('\n"\\')|(L('\\'), ANY)), L('"'))

    def grammar_elem_init(self, sessiondata):
        self.value = self.string

class Item(MyGrammar):
    grammar = REF("NamedList") | REF("AnonList") | Identifier | Number | String

    def grammar_elem_init(self, sessiondata):
        self.value = self[0].value

class AnonList(MyGrammar):
    grammar = (L('('), ZERO_OR_MORE(Item), L(')'))

    def grammar_elem_init(self, sessiondata):
        self.value = [elem.value for elem in self[1]]

class ListIdentifier(MyGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = (WORD("a-zA-Z", "0-9a-zA-Z_"), L('('))

class NamedList(MyGrammar):
    grammar = (ListIdentifier, ZERO_OR_MORE(Item), L(')'))

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        try:
            func = _build_NamedList[name]
        except KeyError:
            func = _build_simple
        try:
            func, kwargs = func
        except TypeError:
            kwargs = {}
        self.value = {name: func([elem.value for elem in self[1]], listname=name, **kwargs)}

class TechFile(MyGrammar):
    grammar = (ONE_OR_MORE(NamedList), OPTIONAL(WHITESPACE))

    def grammar_elem_init(self, sessiondata):
        self.value = {"TechFile": [elem.value for elem in self[0]]}
