from .. import technology as tech, mask, primitive as prim

__all__ = ["technology"]

class _FreePDK45(tech.Technology):
    def __init__(self):
        super().__init__("FreePDK45")

        masks = self.masks
        prims = self.primitives

        self.constraints += (self.grid == 0.0025)

        # Wiki: Layers
        masks += [mask.Mask(name) for name in [
            "active", "nwell", "pwell", "nimplant", "pimplant", "sblock",
            "vthl", "vthg", "vthh", "thkox", "poly", "contact",
            "metal1", "via1", "metal2", "via2", "metal3", "via3", "metal4", "via4", "metal5", "via5",
            "metal6", "via6", "metal7", "via7", "metal8", "via8", "metal9", "via9", "metal10",
        ]]

        # TODO: Find out what Implant.2 is supposed to mean
        #       ""
        # TODO: Find out what MetalTNG.4 is supposed to mean
        #       "Minimum area of metalTNG straddling via[6-8]"

        # wells
        wells = (
            prim.Well(
                implant=impl,
                min_width = 0.200, # Well.4
                min_space = 0.225, # Well.2
                min_space_samenet = 0.135, # Well.3
            ) for impl in (masks.nwell, masks.pwell)
        )
        prims += wells
        # wires
        wires = (prim.Wire(material=mat, **wire_args) for mat, wire_args in (
            (masks.active, {
                "min_width": 0.090, # Active.1
                "min_space": 0.080, # Active.2
            }),
            (masks.poly, {
                "min_width": 0.050, # Poly.1
                "min_space": 0.070, # Poly.6
            }),
            (masks.metal1, {
                "min_width": 0.065, # Metal1.1
                "min_space": 0.065, # Metal1.2
                "space_table": (
                    ((0.090, 0.900), 0.090), # Metal1.5
                    ((0.270, 0.300), 0.270), # Metal1.6
                    ((0.500, 1.800), 0.500), # Metal1.7
                    ((0.900, 2.700), 0.900), # Metal1.8
                    ((1.500, 4.000), 1.500), # Metal1.9
                ),
            }),
            *(
                (metal, {
                    "min_width": 0.070, # MetalInt.1
                    "min_space": 0.070, # MetalInt.2
                    "space_table": (
                        ((0.090, 0.900), 0.090), # MetalInt.5
                        ((0.270, 0.300), 0.270), # MetalInt.6
                        ((0.500, 1.800), 0.500), # MetalInt.7
                        ((0.900, 2.700), 0.900), # MetalInt.8
                        ((1.500, 4.000), 1.500), # MetalInt.9
                    ),
                }) for metal in (masks.metal2, masks.metal3)
            ),
            *(
                (metal, {
                    "min_width": 0.140, # MetalSMG.1
                    "min_space": 0.140, # MetalSMG.2
                    "space_table": (
                        ((0.270, 0.300), 0.270), # MetalSMG.6
                        ((0.500, 1.800), 0.500), # MetalSMG.7
                        ((0.900, 2.700), 0.900), # MetalSMG.8
                        ((1.500, 4.000), 1.500), # MetalSMG.9; added
                    ),
                }) for metal in (masks.metal4, masks.metal5, masks.metal6)
            ),
            *(
                (metal, {
                    "min_width": 0.400, # MetalTNG.1
                    "min_space": 0.400, # MetalTNG.2
                    "space_table": (
                        # MetalTNG.5-6 ignored
                        ((0.500, 1.800), 0.500), # MetalTNG.7; added
                        ((0.900, 2.700), 0.900), # MetalTNG.8; added
                        ((1.500, 4.000), 1.500), # MetalTNG.9; added
                    ),
                }) for metal in (masks.metal7, masks.metal8)
            ),
            *(
                (metal, {
                    "min_width": 0.800, # MetalG.1
                    "min_space": 0.800, # MetalG.2
                    "space_table": (
                        ((0.900, 2.700), 0.900), # MetalG.8
                        ((1.500, 4.000), 1.500), # MetalG.9
                    ),
                }) for metal in (masks.metal9, masks.metal10)
            ),
        ))
        prims += wires
        # vias
        vias = (
            prim.Via(**via_args) for via_args in (
                {
                    "material": masks.contact,
                    "width": 0.065, # Contact.1
                    "min_space": 0.075, # Contact.2
                    "bottom": (prims.active, prims.poly), # Contact.3
                    "top": prims.metal1, # Contact.3
                    "min_bottom_enclosure": 0.005, # Contact.4+5
                    "min_top_enclosure": (0.000, 0.035), # Metal1.3
                },
                {
                    "material": masks.via1,
                    "width": 0.065, # Contact.1
                    "min_space": 0.075, # Contact.2
                    "bottom": prims.metal1, # Contact.3
                    "top": prims.metal2, # Contact.4
                    "min_bottom_enclosure": (0.000, 0.035), # Metal1.4
                    "min_top_enclosure": (0.000, 0.035), # MetalInt.3
                },
                {
                    "material": masks.via2,
                    "width": 0.070, # Via[2-3].1
                    "min_space": 0.085, # Via[2-3].2
                    "bottom": prims.metal2, # Via[2-3].3
                    "top": prims.metal3, # Via[2-3].4
                    "min_bottom_enclosure": (0.000, 0.035), # MetalInt.4
                    "min_top_enclosure": (0.000, 0.035), # MetalInt.4
                },
                {
                    "material": masks.via3,
                    "width": 0.070, # Via[2-3].1
                    "min_space": 0.085, # Via[2-3].2
                    "bottom": prims.metal3, # Via[2-3].3
                    "top": prims.metal4, # Via[2-3].4, MetalSMG.3
                    "min_bottom_enclosure": (0.000, 0.035), # MetalInt.4
                },
                {
                    "material": masks.via4,
                    "width": 0.140, # Via[4-6].1
                    "min_space": 0.160, # Via[4-6].2
                    "bottom": prims.metal4, # Via[4-6].3, MetalSMG.3
                    "top": prims.metal5, # Via[4-6].4, MetalSMG.3
                },
                {
                    "material": masks.via5,
                    "width": 0.140, # Via[4-6].1
                    "min_space": 0.160, # Via[4-6].2
                    "bottom": prims.metal5, # Via[4-6].3, MetalSMG.3
                    "top": prims.metal6, # Via[4-6].4, MetalSMG.3
                },
                {
                    "material": masks.via6,
                    "width": 0.140, # Via[4-6].1
                    "min_space": 0.160, # Via[4-6].2
                    "bottom": prims.metal6, # Via[4-6].3, MetalSMG.3
                    "top": prims.metal7, # Via[4-6].4, MetalTNG.3
                },
                {
                    "material": masks.via7,
                    "width": 0.400, # Via[7-8].1
                    "min_space": 0.440, # Via[7-8].2
                    "bottom": prims.metal7, # Via[7-8].3, MetalTNG.3
                    "top": prims.metal8, # Via[7-8].4, MetalTNG.3
                },
                {
                    "material": masks.via8,
                    "width": 0.400, # Via[7-8].1
                    "min_space": 0.440, # Via[7-8].2
                    "bottom": prims.metal8, # Via[7-8].3, MetalTNG.3
                    "top": prims.metal9, # Via[7-8].4, MetalG.3
                },
                {
                    "material": masks.via9,
                    "width": 0.800, # Via[9].1
                    "min_space": 0.880, # Via[9].2
                    "bottom": prims.metal8, # Via[9].3, MetalG.3
                    "top": prims.metal9, # Via[9].4, MetalG.3
                },
            )
        )
        prims += vias
        
        self.constraints += [
            # Wiki: Well Rules
            masks.nimplant.overlap_with(masks.pimplant) <= 0.000, # Implant.5

            # Wiki: Active Rules
            *[masks.active.enclosed_by(well) >= 0.055 for well in wells], # Active.3
            *[masks.active.space_to(well) >= 0.055 for well in wells], # Active.3
            masks.active.is_inside(masks.nwell, masks.pwell), # Active.4

            # Wiki: Contact Rules
            masks.contact.space_to(masks.poly) >= 0.090, # Contact.7
        ]

        # transistors
        mosfets = [
            prim.MOSFET(name,
                poly=prims.poly, active=prims.active, implant=impl, well=well,
                # No need for overruling min_l, min_w
                min_activepoly_space=0.050, # Poly.5
                min_sd_width=0.070, # Poly.4
                min_polyactive_extension=0.055, # Poly.3
                min_gateimplant_enclosure=0.070, # Implant.1
                min_gate_space=0.140, # Poly.2
                min_contactgate_space=0.035, # Contact.6
            ) for name, impl, well in (
                ("nmos_vtl", (masks.nimplant, masks.vthl), masks.pwell),
                ("pmos_vtl", (masks.pimplant, masks.vthl), masks.nwell),
                ("nmos_vtg", (masks.nimplant, masks.vthg), masks.pwell),
                ("pmos_vtg", (masks.pimplant, masks.vthg), masks.nwell),
                ("nmos_vth", (masks.nimplant, masks.vthh), masks.pwell),
                ("pmos_vth", (masks.pimplant, masks.vthh), masks.nwell),
                ("nmos_thkox", (masks.nimplant, masks.thkox), masks.pwell),
                ("pmos_thkox", (masks.pimplant, masks.thkox), masks.nwell),
            )
        ]
        self.primitives += mosfets
        
tech = technology = _FreePDK45()
