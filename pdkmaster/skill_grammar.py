"""
A modgrammar for Cadence SKILL files

Top Grammar is SkillFile.
This grammar wants to parse all valid SKILL scripts, including Cadence text technology files,
Assura rules etc. This parser may parse invalid SKILL scripts.
"""

import re
from collections import OrderedDict

from modgrammar import *
from modgrammar.extras import *

grammar_whitespace_mode = "optional"
# Include comments in whitespace
grammar_whitespace = re.compile(r'(\s+|;.*?\n|/\*(.|\n)*?\*/)+')

# Override this value to True in user code to enable parser debug output.
_debug = False


#
# Function value generation lookup table
#
# This table allows to customize the value representing a function.
# See Function.grammar_elem_init, how it works.
# A set of functions will be added for each type of SKILL file supported.
#
_value4function_table = {}
_dont_convert_list = []

#
# Technology file support functions
#
def _get_layername(v):
    """Get layer name. Value can be a string or a list of two values for layer purpose
    If purpose is specified it will return a layer name using '.' as delimiter between layername
    and purpose
    """
    if isinstance(v, str):
        return v
    elif len(v) == 1:
        return v[0]
    elif len(v) == 2:
        return v[0]+"."+v[1]
    else:
        raise ValueError("{!r} is not a valid layer specification")

def _get_bool(v):
    assert type(v) is bool
    return v

def _get_combinedlayername(v):
    """Returns a combination of layers, the layers will be separated by a ':' as delimiter.

    This is used for layer pair for design rules or for a triple of layers for via rule"""
    assert len(v) > 1
    return ":".join([_get_layername(elem) for elem in v])

def _get_numornil(v):
    if isinstance(v, bool):
        assert not v
        return None
    else:
        assert isinstance(v, (int, float))
        return v

def _tffunc_prop_value(elems, **kwargs):
    ret = {}
    for v in elems:
        assert 2 <= len(v) <= 4
        prop = v[0]
        value = v[1]
        ret[prop] = value
        if len(v) > 2:
            prop += "."+v[2]
            value = v[3] if len(v) > 3 else True
            ret[prop] = value

    return ret

def _tffunc_prop_layers_value_optextra(elems, **kwargs):
    """data: [prop (layer1 (layer2 (layer3))) value (extraprop (extravalue))]
    if no layer is present "_" will be used for layername"""
    ret = {}
    for v in elems:
        cond = v[0]
        if len(v) == 2:
            layer = "_"
            spec = v[1]
            extra = None
        else:
            end = 2
            while (
                ((type(v[end]) is str) and v[end][0] != "'")
                or ((type(v[end]) is list) and (type(v[end][0]) is str))
            ):
                end += 1
            if end == 2:
                layer = _get_layername(v[1])
            else:
                layer = _get_combinedlayername(v[1:end])
            spec = v[end]
            if len(v) > end+1:
                extra = cond + "." + v[end+1]
                extra_spec = v[end+2] if len(v) > end+2 else True
            else:
                extra = None
        if layer in ret:
            ret[layer][cond] = spec
        else:
            ret[layer] = {cond: spec}
        if extra:
            ret[layer][extra] = extra_spec

    return ret

def _tffunc_prop_cumulative_value(elems, *, functionname, **kwargs):
    d = {}
    for v in elems:
        cond = v[0]
        if functionname == "cumulativeMetalAntenna":
            cond += ".cumulative_metal"
        elif functionname == "cumulativeViaAntenna":
            cond += ".cumulative_via"
        else:
            raise Exception("unhandled name '{}'".format(name))
        d[cond] = v[1]
        if len(v) > 2:
            d[cond + "." + v[2]] = True if len(v) == 3 else v[3]

    return {"_": d}

def _tffunc_prop_value_units(elems, **kwargs):
    ret = {}
    for prop, units, value in elems:
        ret[prop] = [value, units]

    return ret

def _tffunc_layer_value(elems, *, unique=False, **kwargs):
    ret = {}
    for layer, value in elems:
        layername = _get_layername(layer)
        if unique:
            assert layername not in ret
        ret[layername] = value

    return ret

def _tffunc_layer_values(elems, **kwargs):
    ret = {}
    for v in elems:
        ret[_get_layername(v[0])] = v[1:]

    return ret

def _tffunc_layers(elems, **kwargs):
    return [_get_layername(elem) for elem in elems]

def _tffunc_combinedlayers(elems, **kwargs):
    return [_get_combinedlayername(elem) for elem in elems]

def _tffunc_techParams(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) == 2
        paramname = v[0]
        if paramname.endswith("layer") | paramname.endswith("Layer"):
            ret[paramname] = _get_layername(v[1])
        elif paramname.endswith("layers"):
            if not isinstance(v[1], bool):
                ret[paramname] = [_get_layername(layer) for layer in v[1]]
            else:
                assert not v[1]
        else:
            ret[v[0]] = v[1]

    return ret

def _tffunc_name_abbreviation(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) in (2, 3)
        techname = v[0]
        d = {"number": v[1]}
        if len(v) > 2:
            d["abbreviation"] = v[2]
        ret[techname] = d

    return ret

def _tffunc_techDisplays(elems, **kwargs):
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

def _tffunc_standardViaDefs(elems, **kwargs):
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
        if (len(v) > 10) and v[10]:
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

def _tffunc_customViaDefs(elems, **kwargs):
    ret = {}
    for v in elems:
        vianame = v[0]
        assert vianame not in ret
        ret[vianame] ={
            "library": v[1],
            "cell": v[2],
            "view": v[3],
            "layer1": _get_layername(v[4]),
            "layer2": _get_layername(v[5]),
            "resistance": v[6],
        }

    return ret

def _tffunc_spacingTables(elems, **kwargs):
    ret = {}
    for v in elems:
        if isinstance(v[2], list):
            layer = _get_layername(v[1])
            define = v[2]
            table = v[3]
            tail = v[4:]
        elif len(v) > 4:
            layer = _get_combinedlayername(v[1:3])
            define = v[3]
            table = v[4]
            tail = v[5:]
        else:
            raise ValueError("Unexpected spacingTables length")
        assert len(define[0]) == 3 or len(define[0]) == 6
        assert not define[0][1] and not define[0][2]

        d = {
            "index": define[0][0],
        }

        if len(define[0]) > 3:
            assert not define[0][4] and not define[0][5]
            d["index2"] = define[0][3]
        if len(define) > 1:
            d["default"] = define[1]
        if len(define[0]) == 3:
            d["table"] = [[table[2*i], table[2*i+1]] for i in range(len(table)//2)]
        else: # len(define[0]) == 6
            d["table"] = [[*table[2*i], table[2*i+1]] for i in range(len(table)//2)]

        if len(tail) == 1:
            d[tail[0]] = True
        elif len(tail) > 1:
            d[tail[0]] = tail[1]

        if layer in ret:
            ret[layer][v[0]] = d
        else:
            ret[layer] = {v[0]: d}

    return ret

def _tffunc_viaSpecs(elems, **kwargs):
    ret = {}
    for v in elems:
        layer = _get_combinedlayername(v[0:2])
        if len(v[2]) == 1:
            vias = v[2][0]
        else:
            vias = v[2]
        ret[layer] = vias

    return ret

def _tffunc_antennaModels(elems, **kwargs):
    ret = {}
    for v in elems:
        modelname = v[0]
        rules = {}
        for rule in v[1:]:
            for rulename, spec in rule.items():
                if rulename == "antenna":
                    v2 = _tffunc_prop_layers_value_optextra(spec, functionname=rulename)
                elif rulename in ("cumulativeMetalAntenna", "cumulativeViaAntenna"):
                    v2 =  _tffunc_prop_cumulative_value(spec, functionname=rulename)
                else:
                    raise ValueError("Unsupported rulename '{}' for antenneModels".format(rulename))
                for layer, layerspec in v2.items():
                    if layer in rules:
                        rules[layer].update(layerspec)
                    else:
                        rules[layer] = layerspec
        ret[modelname] = rules

    return ret

def _tffunc_constraintGroups(elems, **kwargs):
    ret = {}
    for v in elems:
        groupname = v[0]
        override = _get_bool(v[1])
        constraints = {"override": override}
        if (len(v) > 2) and isinstance(v[2], str):
            constraints["abbreviation"] = v[2]
            start = 3
        else:
            start = 2
        for constraint in v[start:]:
            constraints.update(constraint)
        ret[groupname] = constraints

    return ret

def _tffunc_techDerivedLayers(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) == 3 and len(v[2]) == 3
        if isinstance(v[2][2], (int, float)):
            ret[v[0]] = {
                "number": v[1],
                "layer": _get_layername(v[2][0]),
                v[2][1]: v[2][2],
            }
        else:
            ret[v[0]] = {
                "number": v[1],
                "layer": _get_combinedlayername([v[2][0], v[2][2]]),
                "operation": v[2][1],
            }

    return ret

def _tffunc_equivalentLayers(elems, **kwargs):
    ret = {}
    for layer1, layer2 in elems:
        ret[_get_layername(layer1)] = _get_layername(layer2)

    return ret

def _tffunc_functions(elems, **kwargs):
    ret = {}
    for v in elems:
        assert 2 <= len(v) <= 3
        layer = _get_layername(v[0])
        assert layer not in ret
        ret[layer] = {"function": v[1]}
        if len(v) > 2:
            ret[layer]["mask_number"] = v[2]

    return ret

def _tffunc_multipartPathTemplates(elems, **kwargs):
    ret = {}
    for v in elems:
        assert len(v) == 5

        pathname = v[0]

        v2 = v[1]
        l = len(v2)
        assert 1 <= l <= 9
        d = {"layer": _get_layername(v2[0])}
        if l > 1:
            d["width"] = v2[1]
        if l > 2:
            d["choppable"] = _get_bool(v2[2])
        if l > 3:
            d["endtype"] = v2[3]
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
        if not isinstance(v2, bool):
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
                    d["justification"] = v3[4]
                if l > 5:
                    d["begin_offset"] = v3[5]
                if l > 6:
                    d["end_offset"] = v3[6]
                if l > 7:
                    d["connectivity"] = v3[7]
                subpaths.append(d)
                spec["offset"] = subpaths
        else:
            assert not v2

        v2 = v[3]
        if not isinstance(v2, bool):
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
            assert not v2

        v2 = v[4]
        if not isinstance(v2, bool):
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
                    d["justification"] = v3[5]
                if l > 6:
                    n = _get_numornil(v3[6])
                    if n is not None:
                        d["space"] = n
                if l > 7:
                    d["begin_offset"] = v3[7]
                if l > 8:
                    d["end_offset"] = v3[8]
                if l > 9:
                    d["gap"] = v3[9]
                if l > 10:
                    c = v3[10]
                    if not (isinstance(c, bool) and not c):
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

def _tffunc_streamLayers(elems, **kwargs):
    ret = {}
    for layer, number, datatype, translate in elems:
        layername = _get_layername(layer)
        ret[layername] = {
            "number": number,
            "datatype": datatype,
            "translate": _get_bool(translate),
        }

    return ret

def _tffunc_layerFunctions(elems, **kwargs):
    ret = {}
    for v in elems:
        assert 2 <= len(v) <= 3
        layername = _get_layername(v[0])
        d = {"function": v[1]}
        if len(v) > 2:
            d["masknumber"] = v[2]
        assert layername not in ret
        ret[layername] = d

    return ret

def _tffunc_spacingRules(elems, **kwargs):
    ret = {}
    for v in elems:
        specname = v[0]
        assert 3 <= len(v) <= 4
        if len(v) == 3:
            layername = _get_layername(v[1])
        elif len(v) == 4:
            layername = _get_combinedlayername(v[1:3])
        specvalue = v[-1]
        if layername in ret:
            ret[layername][specname] = specvalue
        else:
            ret[layername] = {specname: specvalue}

    return ret

_value4function_table.update({
    "techLayerPurposePriorities": _tffunc_layers,
    "interconnect": _tffunc_prop_value,
    "viewTypeUnits": _tffunc_prop_value_units,
    "viaLayers": _tffunc_combinedlayers,
    "routingGrids": _tffunc_prop_layers_value_optextra,
    "spacings": _tffunc_prop_layers_value_optextra,
    "orderedSpacings": _tffunc_prop_layers_value_optextra,
    "electrical": _tffunc_prop_layers_value_optextra,
    "orderedElectrical": _tffunc_prop_layers_value_optextra,
    "techLayerProperties": _tffunc_prop_layers_value_optextra,
    "characterizationRules": _tffunc_prop_layers_value_optextra,
    "currentDensity": _tffunc_prop_layers_value_optextra,
    "routingDirections": _tffunc_layer_value,
    "stampLabelLayers": _tffunc_layer_values,
    "compactorLayers": (_tffunc_layer_value, {"unique": True}),
    "techPurposes": _tffunc_name_abbreviation,
    "techLayers": _tffunc_name_abbreviation,
    "techParams": _tffunc_techParams,
    "techDisplays": _tffunc_techDisplays,
    "standardViaDefs": _tffunc_standardViaDefs,
    "customViaDefs": _tffunc_customViaDefs,
    "spacingTables": _tffunc_spacingTables,
    "viaSpecs": _tffunc_viaSpecs,
    "antennaModels": _tffunc_antennaModels,
    "constraintGroups": _tffunc_constraintGroups,
    "techDerivedLayers": _tffunc_techDerivedLayers,
    "equivalentLayers": _tffunc_equivalentLayers,
    "functions": _tffunc_functions,
    "multipartPathTemplates": _tffunc_multipartPathTemplates,
    "streamLayers": _tffunc_streamLayers,
    "layerFunctions": _tffunc_layerFunctions,
    "spacingRules": _tffunc_spacingRules,
    "orderedSpacingRules": _tffunc_spacingRules,
    # Following functions are not directly converted but done inside antennaModels function
    # "antenna": _tffunc_prop_layers_value_optextra,
    # "cumulativeMetalAntenna": _tffunc_prop_cumulative_value,
    # "cumulativeViaAntenna": _tffunc_prop_cumulative_value,
})
_dont_convert_list += ["currentDensity"]

#
# Assura files support functions
#
def _assfunc_layerDefs(elems, **kwargs):
    def parse_type(layerspecs, base, typespec):
        if type(typespec) is list:
            if len(typespec) == 3 and typespec[1] == ":":
                layerspecs.append("{}.{}-{}".format(
                    base, typespec[0], typespec[2]
                ))
            else:
                for v in typespec:
                    parse_type(layerspecs, base, v)
        else:
            layerspecs.append(base+"."+str(typespec))

    name = elems[0]
    d = {}
    for elem in elems[1:]:
        assert len(elem) == 3 and elem[1] == "="
        layername, _, expr = elem
        assert len(expr) == 1
        for layerfunc, layerspec in expr.items():
            assert layerfunc in (
                "cellBoundary", "layer", "text", "textFile", "textToPin", "pinText", "pinLayer",
            )
            if layerfunc == "textFile":
                # TODO: Handle textFile properly
                if "_textFile" not in d:
                    d["_textFile"] = [layerspec]
                else:
                    d["_textFile"].append(layerspec)
            else:
                layerspecs = []
                if len(layerspec) == 2 and type(layerspec[1]) is dict:
                    base = str(layerspec[0])
                    layertype = layerspec[1]
                    assert len(layertype) == 1
                    parse_type(layerspecs, base, layertype["type"])
                else:
                    for l in layerspec:
                        if type(l) is list:
                            if len(l) == 1:
                                layerspecs.append(str(l[0]))
                            elif len(l) == 2:
                                base = str(l[0])
                                layertype = l[1]
                                assert len(layertype) == 1
                                parse_type(layerspecs, base, layertype["type"])
                            else:
                                raise ValueError("type dict expected as second element in {!r}".format(l))
                        else:
                            layerspecs.append(str(l))
                if len(layerspecs) == 1:
                    layerspecs = layerspecs[0]
                d[layername] = {layerfunc: layerspecs}

    return {name: d}

def _assfunc_drcExtractRules(elems, *, top=True, unknownfuncs=set(), **kwars):
    _known_funcs = {
        "if", "when", "for", "foreach", "evalstring", "sprintf", "let", "prog", "lambda",
        "abs", "exp", "fix", "sqrt",
        "minusp", "plusp", "zerop", # Are these build in ?
        "gate", "antenna", "measure", "calculate", "area", "layerList", "via", "output",
        "cellView", "termOrder",
        "buttOrOver", "drc", "drcAntenna", "errorLayer", "flatErrorLayer", "offGrid", "overlap",
        "keepLayer", "rcxLayer",
        "geomAnd", "geomAndNot", "geomAvoiding", "geomBkgnd", "geomButting", "geomButtOnly",
        "geomButtOrCoin", "geomButtOrOver",
        "geomCat", "geomConnect", "geomContact", "geomContactCheck",
        "geomEmpty", "geomEnclose", "geomEncloseRect",
        "geomGetAdjacentEdge", "geomGetAngledEdge", "geomGetBBox", "geomGetCorner", "geomGetCoverage",
        "geomGetEdge", "geomGetHoled", "geomGetLength", "geomGetNet", "geomGetNon45", "geomGetNon90",
        "geomGetRectangle", "geomGetTexted", "geomGetUnTexted", "geomGetVertex", "geomGrow",
        "geomHoles",
        "geomInside", "geomInsidePerShapeArea",
        "geomNodeRelate", "geomNoHoles",
        "geomOr", "geomOutside", "geomOverlap",
        "geomSize", "geomSizeAnd", "geomSizeAndNot", "geomSizeAndProc", "geomStamp", "geomStraddle",
        "geomStretch", "geomStretchCorner",
        "geomTextShape",
        "geomWidth", "geomXor",
        "generateRectangle",
        "processAntenna", "processCoverage",
        "bulkLayers", "edgeLayers", "withinLayer",
        "attachParameter", "measureParameter", "nameParameter",
        "measureProximity2", "measureSTI",
        "calculateEdges4", "calculateExp", "calculateParameter",
        "extractBJT", "extractCAP", "extractDevice", "extractDIODE", "extractMOS", "extractRES",
        "spiceModel", "targetLayer",
        "saveInterconnect", "saveProperty", "saveRecognition",
        "diffusion", #?
        "label", #?
        "shielded", #?
        "resetCumulative", #?
        "svia", #?
        "step", #?
    }

    _dont_scan = {
        "extractBJT", "extractCAP", "extractDevice", "extractDIODE", "extractMOS", "extractRES",
    }

    def _scan4unknownfuncs(elem):
        if isinstance(elem, dict):
            for funcname, args in elem.items():
                if funcname not in _known_funcs:
                    unknownfuncs.add(funcname)
                _scan4unknownfuncs(args)
        elif isinstance(elem, list):
            for v in elem:
                _scan4unknownfuncs(v)

    begin = 0
    value = {
        "layerDefs": {},
        "procedures": {},
        "statements": [],
    }
    for elem in elems:
        if isinstance(elem, dict):
            assert len(elem) == 1
            for key, body in elem.items():
                if key == "layerDefs":
                    value["layerDefs"].update(body)
                elif key == "procedure":
                    header = body[0]
                    assert type(header) is dict and len(header) == 1
                    for funcname, args in header.items():
                        subvalue = _assfunc_drcExtractRules(body[1:], top=False, unknownfuncs=unknownfuncs)
                        assert "layerDefs" not in subvalue
                        value["procedures"][funcname] = {
                            "args": args,
                            "body": subvalue["statements"],
                        }
                elif key in ("if", "ivIf"):
                    thenidx = None
                    elseidx = None
                    for i, item in enumerate(body):
                        if type(item) is str:
                            if item == "then":
                                thenidx = i
                            if item == "else":
                                elseidx = i
                    assert thenidx is not None, "only then syntax supported for if"
                    d = {
                        "cond": body[:thenidx],
                        "then": _assfunc_drcExtractRules(body[thenidx+1:elseidx], top=False, unknownfuncs=unknownfuncs)
                    }
                    assert "procedures" not in d["then"]
                    if elseidx is not None:
                        d["else"] = _assfunc_drcExtractRules(body[elseidx+1:], top=False, unknownfuncs=unknownfuncs)
                        assert "procedures" not in d["else"]
                    value["statements"].append({"if": d})
                elif key == "let":
                    d = {"vars": body[0]}
                    d.update(_assfunc_drcExtractRules(body[1:], top=False, unknownfuncs=unknownfuncs))
                else:
                    if key not in _dont_scan:
                        _scan4unknownfuncs(elem)
                    value["statements"].append(elem)
            begin += 1
        else:
            _scan4unknownfuncs(elem)
            value["statements"].append(elem)
            begin += 1

    if len(value["layerDefs"]) == 0:
        value.pop("layerDefs")

    if len(value["procedures"]) == 0:
        value.pop("procedures")
    else:
        unknownfuncs -= set(value["procedures"].keys())

    if top and len(unknownfuncs) > 0:
        print("Unknown functions in drcExtractRules:")
        for func in unknownfuncs:
            print("\t{}".format(func))
        raise(ValueError)

    return value

_value4function_table.update({
    "layerDefs": _assfunc_layerDefs,
    "drcExtractRules": _assfunc_drcExtractRules,
    #TODO: avCompareRules
})


#
# SKILL Grammar
#
class _BaseGrammar(Grammar):
    def __init__(self, *args):
        super().__init__(*args)
        if _debug:
            start = self._str_info[1]
            end = self._str_info[2]
            print("{}: {}-{}".format(self.__class__.__name__, start, end))

class Symbol(_BaseGrammar):
    grammar = RE(r"'[a-zA-Z_][a-zA-Z0-9_]*")

    def grammar_elem_init(self, sessiondata):
        self.value = self.string[1:]
        self.ast = {"Symbol": self.value}

class Bool(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = L("t")|L("nil"), NOT_FOLLOWED_BY(WORD("a-zA-Z0-9_"))

    def grammar_elem_init(self, sessiondata):
        self.value = self.string == "t"
        self.ast = {"Bool": self.value}

class Identifier(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = WORD("a-zA-Z_?@", "a-zA-Z0-9_?@."), NOT_FOLLOWED_BY(L("("))

    def grammar_elem_init(self, sessiondata):
        self.ast = {"Identifier": self.string}
        self.value = self.string

class Number(_BaseGrammar):
    grammar = RE(r"(\+|-)?([0-9]+(\.[0-9]*)?|\.[0-9]+)(e(\+|-)?[0-9]+)?")

    def grammar_elem_init(self, sessiondata):
        isfloat = ("." in self.string) or ("e" in self.string)
        self.value = float(self.string) if isfloat else int(self.string)
        self.ast = {"Number": self.value}

class String(_BaseGrammar):
    grammar = RE(r'"([^"\\]+|\\(.|\n))*"')

    def grammar_elem_init(self, sessiondata):
        self.value = self.string[1:-1]
        self.ast = {"String": self.value}

class PrefixOperator(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = L("!") | RE(r"\+(?!(\+|[0-9]))") | RE(r"\-(?!(\-|[0-9]))")

class PostfixOperator(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = L("++") | L("--")

class BinaryOperator(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = (
        L("=") | L(":") | L("<") | L(">") | L("<=") | L(">=") | L("==") | L("!=") | L("<>") |
        RE(r"\+(?!(\+|[0-9]))") | RE(r"\-(?!(\-|[0-9]))") |
        L("*") | L("/") |
        L("&") | L("|") | L("&&") | L("||") |
        L(",")
    )

class FieldOperator(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = L("->") | L("~>")

class ItemBase(_BaseGrammar):
    grammar_whitespace_mode = "explicit"
    grammar = (
        REF("Function") | REF("ArrayElement") | REF("List") | REF("SymbolList") | REF("CurlyList") |
        Bool | Identifier | Symbol | Number | String
    ), ZERO_OR_MORE(FieldOperator, Identifier)

    def grammar_elem_init(self, sessiondata):
        if len(self[1]) == 0:
            ast = self[0].ast
            value = self[0].value
        else:
            ast = [self[0].ast]
            value = [self[0].value]
            for op, ident in self[1]:
                ast += [op.string, ident.ast]
                value += [op.string, ident.value]
        self.ast = {"ItemBase": ast}
        self.value = value

class Item(_BaseGrammar):
    grammar = ZERO_OR_MORE(PrefixOperator), ItemBase, ZERO_OR_MORE(PostfixOperator)

    def grammar_elem_init(self, sessiondata):
        if len(self[0]) == 0 and len(self[2]) == 0:
            ast = self[1].ast
            value = self[1].value
        else:
            ast = [*[op.string for op in self[0]], self[1].ast, *[op.string for op in self[2]]]
            value = [*[op.string for op in self[0]], self[1].value, *[op.string for op in self[2]]]
        self.ast = {"Item": ast}
        self.value = value

class Expression(_BaseGrammar):
    grammar = Item, ZERO_OR_MORE(BinaryOperator, Item)

    def grammar_elem_init(self, sessiondata):
        if len(self[1]) == 0:
            ast = self[0].ast
            value = self[0].value
        else:
            ast = [self[0].ast]
            value = [self[0].value]
            for op, item in self[1]:
                ast += [op.string, item.ast]
                value += [op.string, item.value]
        self.ast = {"Expression": ast}
        self.value = value

class List(_BaseGrammar):
    grammar = L("("), ZERO_OR_MORE(Expression), L(")")

    def grammar_elem_init(self, sessiondata):
        # Convert list to function if name of first identifier is in _value4function_table
        # and not in the _dont_convert_list
        isfunction = (
            (len(self[1].elements) > 0)
            and (type(self[1][0].value) is str)
            and (self[1][0].value in _value4function_table)
            and (self[1][0].value not in _dont_convert_list)
        )
        if not isfunction:
            self.value = [elem.value for elem in self[1]]
            self.ast = {"List": [elem.ast for elem in self[1]]}
        else:
            name = self[1][0].value
            elems = [elem.value for elem in self[1].elements[1:]]
            func = _value4function_table[name]
            if type(func) == tuple:
                func, kwargs = func
            else:
                kwargs = {}
            self.value = {name: func(elems, functionname=name, **kwargs)}

            self.ast = {"ListFunction": {
                "name": name,
                "args": [elem.ast for elem in self[1].elements[1:]],
            }}

class SymbolList(_BaseGrammar):
    grammar = L("'("), ZERO_OR_MORE(Expression), L(")")

    def grammar_elem_init(self, sessiondata):
        self.value = [elem.value for elem in self[1]]
        self.ast = {"SymbolList": [elem.ast for elem in self[1]]}

class CurlyList(_BaseGrammar):
    grammar = L("{"), ZERO_OR_MORE(Expression), L("}")

    def grammar_elem_init(self, sessiondata):
        self.value = {"{}": [elem.value for elem in self[1]]}
        self.ast = {"CurlyList": [elem.ast for elem in self[1]]}

class Function(_BaseGrammar):
    grammar = RE(r"[a-zA-Z][a-zA-Z0-9_]*\("), ZERO_OR_MORE(Expression), L(')')

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        elems = [elem.value for elem in self[1]]
        try:
            func = _value4function_table[name]
        except KeyError:
            self.value = {name: elems}
        else:
            if type(func) == tuple:
                func, kwargs = func
            else:
                kwargs = {}
            self.value = {name: func(elems, functionname=name, **kwargs)}

        self.ast = {"Function": {
            "name": name,
            "args": [elem.ast for elem in self[1]]
        }}

class ArrayElement(_BaseGrammar):
    grammar = RE(r"[a-zA-Z][a-zA-Z0-9_]*\["), Expression, L(']')

    def grammar_elem_init(self, sessiondata):
        name = self[0].string[:-1]
        self.value = {"Array:"+name: self[1].value}
        self.ast = {"ArrayElem": {
            "name": name,
            "elem": self[1].ast
        }}

class SkillFile(_BaseGrammar):
    grammar = G(ONE_OR_MORE(Expression), OPTIONAL(WHITESPACE))

    def grammar_elem_init(self, sessiondata):
        self.ast = {"SkillFile": [elem.ast for elem in self[0][0]]}
        self.value = {"SkillFile": [elem.value for elem in self[0][0]]}
