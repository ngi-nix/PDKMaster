from .skill_grammar import SkillFile, _skill_if

__all__ = ["AssuraFile"]

#
# Assura function support
#
def _layerDefs(elems, **kwargs):
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

def _drcExtractRules(elems, *, top=True, unknownfuncs=set(), **kwars):
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
                if funcname in ("if", "let", "for", "foreach"):
                    for _, args2 in args.items():
                        _scan4unknownfuncs(args2)
                elif funcname not in _dont_scan:
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
                        subvalue = _drcExtractRules(body[1:], top=False, unknownfuncs=unknownfuncs)
                        assert "layerDefs" not in subvalue
                        value["procedures"][funcname] = {
                            "args": args,
                            "body": subvalue["statements"],
                        }
                elif key in ("if", "ivIf", "when"):
                    d = dict(
                        (
                            key,
                            statements if key == "cond" else _drcExtractRules(
                                statements, top=False, unknownfuncs=unknownfuncs
                            )
                        ) for key, statements in body.items()
                    )
                    assert "procedures" not in d["then"]
                    if "else" in d:
                        assert "procedures" not in d["else"]
                    value["statements"].append({"if": d}) # Convert all to if
                elif key in ("let", "prog"):
                    d = {"vars": body["vars"]}
                    d.update(_drcExtractRules(body["statements"], top=False, unknownfuncs=unknownfuncs))
                    value["statements"].append({"let": d})
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

_value4function_table = {
    "layerDefs": _layerDefs,
    "drcExtractRules": _drcExtractRules,
    "ivIf": _skill_if, # Treat as if alias
    #TODO: avCompareRules
}

#
# Grammar
#
class AssuraFile(SkillFile):
    def grammar_elem_init(self, sessiondata):
        super().grammar_elem_init(sessiondata)
        self.ast = {"AssuraFile": self.ast["SkillFile"]}
        self.value = {"AssuraFile": self.value["SkillFile"]}

    @classmethod
    def parse_string(cls, text):
        return super(AssuraFile, cls).parse_string(text, value4funcs=_value4function_table)
