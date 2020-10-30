from textwrap import dedent
from itertools import product
from xml.etree import ElementTree as ET

from pdkmaster.technology import  property_ as prp, wafer, mask as msk, edge as edg

__all__= ["Generator"]


def _str_mask(mask):
    if isinstance(mask, (msk.DesignMask, msk._MaskAlias)):
        name = mask.name
        if name[0] in "0123456789":
            name = "_" + name
        return name.replace(".", "_").replace(":", "_C_")
    elif mask == wafer:
        return "extent"
    # Handled on higher level
    # elif isinstance(mask, msk._PartsWith):
    #    pass
    elif isinstance(mask, msk.Join):
        return f"({'+'.join(_str_mask(m) for m in mask.masks)})"
    elif isinstance(mask, msk.Intersect):
        return f"({'&'.join(_str_mask(m) for m in mask.masks)})"
    elif isinstance(mask, msk._MaskRemove):
        return f"({_str_mask(mask.from_)}-{_str_mask(mask.what)})"
    # elif isinstance(mask, msk.SameNet):
    #     pass
    assert False


def _str_edge(edge):
    if isinstance(edge, edg.MaskEdge):
        return f"{_str_mask(edge.mask)}.edges"
    elif isinstance(edge, edg._DualEdgeOperation):
        s_edge1 = _str_edge(edge.edge1)
        if isinstance(edge.edge2, msk._Mask):
            s_edge2 = _str_mask(edge.edge2)
        elif isinstance(edge.edge2, edg._Edge):
            s_edge2 = _str_edge(edge.edge2)
        else:
            raise TypeError(f"Unexpected type for edge2 of {str(edge)}")
        op = edge.operation
        if op == "interact_with":
            return f"{s_edge1}.interacting({s_edge2})"
    elif isinstance(edge, edg.Join):
        s_join = "+".join(
            _str_mask(e) if isinstance(e, msk._Mask) else _str_edge(e)
            for e in edge.edges
        )
        return f"({s_join})"
    elif isinstance(edge, edg.Intersect):
        s_join = "&".join(
            _str_mask(e) if isinstance(e, msk._Mask) else _str_edge(e)
            for e in edge.edges
        )
        return f"({s_join})"
    assert False


def _str_designmask(mask):
    assert (
        isinstance(mask, msk.DesignMask)
        and isinstance(mask.gds_layer, tuple)
        and len(mask.gds_layer) == 2
    ), "Internal error"

    return f"{_str_mask(mask)} = input{mask.gds_layer}\n"


def _str_alias(mask):
    assert isinstance(mask, msk._MaskAlias), "Internal error"

    return f"{_str_mask(mask)} = {_str_mask(mask.mask)}\n"


def _str_grid(mask, grid):
    return f"{_str_mask(mask)}.ongrid({grid})\n"


def _str_ge(left, right):
    if isinstance(left, msk._MaskProperty):
        s_mask = _str_mask(left.mask)
        prop = left.prop_name
        if prop in {"width", "space"}:
            return dedent(f"""
                {s_mask}.{prop}({right}).output(
                    "{s_mask} {prop}", "{s_mask} minimum {prop}: {right}µm"
                )
            """[1:])
        elif left.prop_name == "area":
            return dedent(f"""
                {s_mask}.with_area(nil, {right}).output(
                    "{s_mask} area", "{s_mask} minimum area: {right}µm"
                )
            """[1:])
        elif left.prop_name == "density":
            return dedent(f"""
                {s_mask}_mindens = polygon_layer
                dens_check({s_mask}_mindens, {s_mask}, {right}, 1)
                {s_mask}_mindens.output(
                    "{s_mask} density", "{s_mask} minimum density: {round(100*right)}%"
                )
            """[1:])
    elif isinstance(left, msk._DualMaskProperty):
        prop = left.prop_name
        # Special handling of width based spacing rules
        if (prop == "space") and isinstance(left.mask1, msk._PartsWith):
            assert len(left.mask1.condition) == 1
            cond = left.mask1.condition[0]
            assert isinstance(cond, prp.Operators.GreaterEqual)
            assert isinstance(cond.left, msk._MaskProperty)
            assert cond.left.prop_name == "width"
            s_mask = _str_mask(left.mask1.mask)
            return dedent(f"""
                space4width_check({s_mask}, {cond.right}, {right}).output(
                    "{s_mask} table spacing",
                    "Minimum {s_mask} spacing for {cond.right}µm width: {right}µm"
                )
            """[1:])
        s_mask1 = _str_mask(left.mask1)
        s_mask2 = _str_mask(left.mask2)
        if prop == "space":
            return dedent(f"""
                {s_mask1}.separation({s_mask2}, {right}, square).output(
                    "{s_mask1}:{s_mask2} spacing",
                    "Minimum spacing between {s_mask1} and {s_mask2}: {right}µm"
                )
            """[1:])
        elif prop == "overlapwidth":
            return dedent(f"""
                ({s_mask1}&{s_mask2}).width({right}).output(
                    "{s_mask1}:{s_mask2} overlap width",
                    "Minimum overlap widht of {s_mask1} and {s_mask2}: {right}µm"
                )
            """[1:])
        elif prop == "extend_over":
            return dedent(f"""
                extend_check({s_mask2}, {s_mask1}, {right}).output(
                    "{s_mask1}:{s_mask2} extension",
                    "Minimum extension of {s_mask1} of {s_mask2}: {right}µm"
                )
            """[1:])
    elif isinstance(left, msk._DualMaskEnclosureProperty):
        s_mask1 = _str_mask(left.mask1)
        s_mask2 = _str_mask(left.mask2)
        prop = left.prop_name
        if prop == "enclosed_by":
            if isinstance(right.spec, float):
                return dedent(f"""
                    {s_mask2}.enclosing({s_mask1}, {right.spec}).output(
                        "{s_mask2}:{s_mask1} enclosure",
                        "Minimum enclosure of {s_mask2} around {s_mask1}: {right.spec}µm"
                    )
                """[1:])
            else:
                s_desc = (
                    f"Minimum enclosure of {s_mask2} around {s_mask1}: "
                    f"{right.min()}µm minimum, {right.max()}µm opposite"
                )
                return dedent(f"""
                    oppenc_check({s_mask1}, {s_mask2}, {right.min()}, {right.max()}).output(
                        "{s_mask2}:{s_mask1} asymmetric enclosure",
                        "{s_desc}"
                    )
                """[1:])
    elif isinstance(left, edg._EdgeProperty):
        s_edge = _str_edge(left.edge)
        prop = left.prop_name
        if prop == "length":
            return dedent(f"""
                {s_edge}.with_length(nil, {right}).output(
                    "{s_edge} length",
                    "Minimum length of {s_edge}: {right}µm"
                )
            """[1:])
    elif isinstance(left, edg._DualEdgeProperty):
        s_edge1 = _str_edge(left.edge1)
        s_edge2 = (
            _str_mask(left.edge2)+".edges" if isinstance(left.edge2, msk._Mask)
            else _str_edge(left.edge2)
        )
        prop = left.prop_name
        if prop == "enclosed_by":
            return dedent(f"""
                {s_edge2}.enclosing({s_edge1}, {right}).output(
                    "{s_edge2}:{s_edge1} enclosure",
                    "Minimum enclosure of {s_edge2} around {s_edge1}: {right}µm"
                )
            """[1:])
    assert False


def _str_eq(left, right):
    if isinstance(left, msk._MaskProperty):
        s_mask = _str_mask(left.mask)
        prop = left.prop_name
        if prop == "width":
            return dedent(f"""
                width_check({s_mask}, {right}).output(
                    "{s_mask} width", "{s_mask} width: {right}µm"
                )
            """[1:])
        elif prop == "area":
            if round(right, 6) != 0.0:
                raise ValueError("For area equal check value can only be 0.0")
            return f'{s_mask}.output("{s_mask} empty")\n'
    elif isinstance(left, edg._EdgeProperty):
        s_edge = _str_edge(left.edge)
        prop = left.prop_name
        if prop == "length":
            if round(right, 6) != 0.0:
                raise ValueError("For length equal check value can only be 0.0")
            return f'{s_edge}.output("{s_edge} empty")\n'
    assert False


def _str_conn(conn):
    return "".join(
        f"connect({_str_mask(mask1)}, {_str_mask(mask2)})\n"
        for mask1, mask2 in product(conn.mask1, conn.mask2)
    )


def _str_rule(rule):
    s = f"# {rule}\n"
    try:
        if isinstance(rule, prp.Operators.GreaterEqual):
            return s + _str_ge(rule.left, rule.right)
        elif isinstance(rule, prp.Operators.Equal):
            return s + _str_eq(rule.left, rule.right)
        elif isinstance(rule, msk._MaskAlias):
            return s + _str_alias(rule)
        elif isinstance(rule, msk.Connect):
            return s + _str_conn(rule)
    except AssertionError:
        return s + "# Not supported\n"
    else:
        return s + "# Not supported\n"


class Generator:
    def __init__(self, tech):
        self.tech = tech

    def __call__(self):
        return {
            "drc": self._s_drc(),
            "ly_drc": self._s_ly_drc(),
        }

    def _s_drc(self):
        s = dedent(f"""
            # Autogenerated file. Changes will be overwritten.

            source(ENV["SOURCE_FILE"])
            report("{self.tech.name} DRC", ENV["REPORT_FILE"])

        """[1:])

        return s + self._s_drcrules()

    def _s_ly_drc(self):
        ly_drc = ET.Element("klayout-macro")
        ET.SubElement(ly_drc, "description")
        ET.SubElement(ly_drc, "version")
        ET.SubElement(ly_drc, "category").text = "drc"
        ET.SubElement(ly_drc, "prolog")
        ET.SubElement(ly_drc, "epilog")
        ET.SubElement(ly_drc, "doc")
        ET.SubElement(ly_drc, "autorun").text = "false"
        ET.SubElement(ly_drc, "autorun-early").text = "false"
        ET.SubElement(ly_drc, "shortcut")
        ET.SubElement(ly_drc, "show-in-menu").text = "true"
        ET.SubElement(ly_drc, "group-name").text = "drc_scripts"
        ET.SubElement(ly_drc, "menu-path").text = "tools_menu.drc.end"
        ET.SubElement(ly_drc, "interpreter").text = "dsl"
        ET.SubElement(ly_drc, "dsl-interpreter-name").text = "drc-dsl-xml"
        s = dedent(f"""
            # Autogenerated file. Changes will be overwritten.
            
            report("{self.tech.name} DRC")

        """[1:]) + self._s_drcrules()
        ET.SubElement(ly_drc, "text").text = s
        
        return ly_drc

    def _s_drcrules(self):
        s = dedent(f"""
            def width_check(layer, w)
                small = layer.width(w).polygons
                big = layer.sized(-0.5*w).size(0.5*w)

                small | big
            end

            def space4width_check(layer, w, s)
                big = layer.sized(-0.5*w).size(0.5*w)
                big.edges.separation(layer.edges, s)
            end

            def oppenc_check(inner, outer, min, max)
                toosmall = outer.enclosing(inner, min).second_edges

                smallenc = outer.enclosing(inner, max - 1.dbu, projection).second_edges
                # These edges may not touch each other
                touching = smallenc.width(1.dbu, angle_limit(100)).edges

                inner.interacting(toosmall + touching)
            end

            def extend_check(base, extend, e)
                extend.enclosing(base, e).first_edges.not_interacting(base)
            end

            def dens_check(output, input, min, max)
                tp = RBA::TilingProcessor::new

                tp.output("res", output.data)
                tp.input("input", input.data)
                tp.dbu = 1.dbu  # establish the real database unit
                tp.var("vmin", min)
                tp.var("vmax", max)

                tp.queue("_tile && (var d = to_f(input.area(_tile.bbox)) / to_f(_tile.bbox.area); (d < vmin || d > vmax) && _output(res, _tile.bbox))")
                tp.execute("Density check")
            end
        """[1:])

        s += "\n# Define layers\n"
        dms = tuple(self.tech.rules.tt_iter_type(msk.DesignMask))
        s += "".join(_str_designmask(dm) for dm in dms)

        s += "\n# Grid check\n"
        gridrules = tuple(filter(
                lambda rule: (
                    isinstance(rule, prp.Operators.Equal)
                    and isinstance(rule.left, msk._MaskProperty)
                    and (rule.left.prop_name == "grid")
                ),
                self.tech.rules,
            )
        )
        gridspecs = {
            gridrule.left.mask: gridrule.right
            for gridrule in gridrules
        }
        globalgrid = gridspecs[wafer]
        s += "".join(
            _str_grid(dm, gridspecs.get(dm, globalgrid))
            for dm in dms
        )

        s += "\n# Connectivity\n"
        conns = tuple(self.tech.rules.tt_iter_type(msk.Connect))
        s += "".join(_str_rule(conn) for conn in conns)

        s += "\n# DRC rules\n" + "".join(
            _str_rule(rule) for rule in filter(
                lambda rule: rule not in dms + gridrules + conns, self.tech.rules
            )
        )

        return s
