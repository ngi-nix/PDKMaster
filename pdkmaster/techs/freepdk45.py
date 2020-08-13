from ..technology import technology_ as tech, mask as msk, primitive as prm

__all__ = ["technology"]

class _FreePDK45(tech.Technology):
    name = "FreePDK45"
    grid = 0.0025
    substrate_type = "undoped"

    def _init(self):
        prims = self._primitives

        # TODO: Find out what Implant.2 is supposed to mean
        #       ""
        # TODO: Find out what MetalTNG.4 is supposed to mean
        #       "Minimum area of metalTNG straddling via[6-8]"

        # single mask based primitives
        prims += (
            # implants
            *(
                prm.Implant(implant, type_=type_,
                    min_width=0.045, # Implant.3
                    min_space=0.045, # Implant.4
                ) for implant, type_ in (
                    ("nimplant", "n"),
                    ("pimplant", "p"),
                    ("vthl", "adjust"),
                    ("vthg", "adjust"),
                    ("vthh", "adjust"),
                )
            ),
            # wells
            *(
                prm.Well(impl, type_=type_,
                    min_width = 0.200, # Well.4
                    min_space = 0.225, # Well.2
                    min_space_samenet = 0.135, # Well.3
                ) for impl, type_ in (
                    ("nwell", "n"),
                    ("pwell", "p"),
                )
            ),
            # depositions
            prm.Deposition("thkox",
                min_width=0.045, # Own rule
                min_space=0.045, # Own rule
            ),
            # markers
            prm.Marker(name="sblock"),
        )

        # wires
        prims += (
            *(prm.Wire(name, **wire_args) for name, wire_args in (
                ("active", {
                    "min_width": 0.090, # Active.1
                    "min_space": 0.080, # Active.2
                    "enclosed_by": (prims.nwell, prims.pwell), # Active.4
                    "min_enclosure": 0.055, # Active.3
                }),
                ("poly", {
                    "min_width": 0.050, # Poly.1
                    "min_space": 0.070, # Poly.6
                }),
                ("metal1", {
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
                    }) for metal in ('metal2', "metal3")
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
                    }) for metal in ("metal4", "metal5", "metal6")
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
                        "grid": 0.010, # Added rule
                    }) for metal in ("metal7", "metal8")
                ),
                *(
                    (metal, {
                        "min_width": 0.800, # MetalG.1
                        "min_space": 0.800, # MetalG.2
                        "space_table": (
                            ((0.900, 2.700), 0.900), # MetalG.8
                            ((1.500, 4.000), 1.500), # MetalG.9
                        ),
                        "grid": 0.010, # Added rule
                    }) for metal in ("metal9", "metal10")
                ),
            )),
        )

        # vias
        prims += (
            *(
                prm.Via(**via_args) for via_args in (
                    {
                        "name": "contact",
                        "width": 0.065, # Contact.1
                        "min_space": 0.075, # Contact.2
                        "bottom": (prims.active, prims.poly), # Contact.3
                        "top": prims.metal1, # Contact.3
                        "min_bottom_enclosure": 0.005, # Contact.4+5
                        "min_top_enclosure": (0.000, 0.035), # Metal1.3
                    },
                    {
                        "name": "via1",
                        "width": 0.065, # Contact.1
                        "min_space": 0.075, # Contact.2
                        "bottom": prims.metal1, # Contact.3
                        "top": prims.metal2, # Contact.4
                        "min_bottom_enclosure": (0.000, 0.035), # Metal1.4
                        "min_top_enclosure": (0.000, 0.035), # MetalInt.3
                    },
                    {
                        "name": "via2",
                        "width": 0.070, # Via[2-3].1
                        "min_space": 0.085, # Via[2-3].2
                        "bottom": prims.metal2, # Via[2-3].3
                        "top": prims.metal3, # Via[2-3].4
                        "min_bottom_enclosure": (0.000, 0.035), # MetalInt.4
                        "min_top_enclosure": (0.000, 0.035), # MetalInt.4
                    },
                    {
                        "name": "via3",
                        "width": 0.070, # Via[2-3].1
                        "min_space": 0.085, # Via[2-3].2
                        "bottom": prims.metal3, # Via[2-3].3
                        "top": prims.metal4, # Via[2-3].4, MetalSMG.3
                        "min_bottom_enclosure": (0.000, 0.035), # MetalInt.4
                    },
                    {
                        "name": "via4",
                        "width": 0.140, # Via[4-6].1
                        "min_space": 0.160, # Via[4-6].2
                        "bottom": prims.metal4, # Via[4-6].3, MetalSMG.3
                        "top": prims.metal5, # Via[4-6].4, MetalSMG.3
                    },
                    {
                        "name": "via5",
                        "width": 0.140, # Via[4-6].1
                        "min_space": 0.160, # Via[4-6].2
                        "bottom": prims.metal5, # Via[4-6].3, MetalSMG.3
                        "top": prims.metal6, # Via[4-6].4, MetalSMG.3
                    },
                    {
                        "name": "via6",
                        "width": 0.140, # Via[4-6].1
                        "min_space": 0.160, # Via[4-6].2
                        "bottom": prims.metal6, # Via[4-6].3, MetalSMG.3
                        "top": prims.metal7, # Via[4-6].4, MetalTNG.3
                    },
                    {
                        "name": "via7",
                        "width": 0.400, # Via[7-8].1
                        "min_space": 0.440, # Via[7-8].2
                        "bottom": prims.metal7, # Via[7-8].3, MetalTNG.3
                        "top": prims.metal8, # Via[7-8].4, MetalTNG.3
                        "grid": 0.010, # Added rule
                    },
                    {
                        "name": "via8",
                        "width": 0.400, # Via[7-8].1
                        "min_space": 0.440, # Via[7-8].2
                        "bottom": prims.metal8, # Via[7-8].3, MetalTNG.3
                        "top": prims.metal9, # Via[7-8].4, MetalG.3
                        "grid": 0.010, # Added rule
                    },
                    {
                        "name": "via9",
                        "width": 0.800, # Via[9].1
                        "min_space": 0.880, # Via[9].2
                        "bottom": prims.metal9, # Via[9].3, MetalG.3
                        "top": prims.metal10, # Via[9].4, MetalG.3
                        "grid": 0.010, # Added rule
                    },
                )
            ),
        )

        # misc using wires
        prims += (
            # taps
            *(
                prm.DerivedWire(name=name, wire=prims.active, marker=marker, connects=well)
                for name, marker, well in (
                    ("ntap", (prims.nimplant, prims.nwell), prims.nwell),
                    ("ptap", (prims.pimplant, prims.pwell), prims.pwell),
                )
            ),
            # resistors
            *(
                prm.DerivedWire(name, wire=wire, marker=prims.sblock)
                for name, wire in (
                    ("active_res", prims.active),
                    ("poly_res", prims.poly),
                )
            ),
            # extra space rules
            prm.Spacing(primitives1=prims.active, primitives2=prims.poly, min_space=0.050), # Poly.5
            prm.Spacing(primitives1=prims.contact, primitives2=prims.poly, min_space=0.090),
        )

        # transistors
        prims += (
            prm.MOSFETGate("mosgate",
                poly=prims.poly, active=prims.active,
                # No need for overruling min_l, min_w
                min_sd_width=0.070, # Poly.4
                min_polyactive_extension=0.055, # Poly.3
                contact=prims.contact, min_contactgate_space=0.035, # Contact.6
                min_gate_space=0.140, #
            ),
            prm.MOSFETGate("thkmosgate",
                poly=prims.poly, active=prims.active, oxide=prims.thkox,
                min_l=0.060, # Added rule
                min_sd_width=0.070, # Poly.4
                min_polyactive_extension=0.055, # Poly.3
                contact=prims.contact, min_contactgate_space=0.035, # Contact.6
                min_gate_space=0.140, #
            ),
        )
        prims += (
            prm.MOSFET(name,
                gate=gate, implant=impl, well=well,
                min_gateimplant_enclosure=0.070, # Implant.1
            ) for name, gate, impl, well in (
                ("nmos_vtl", prims.mosgate, (prims.nimplant, prims.vthl), prims.pwell),
                ("pmos_vtl", prims.mosgate, (prims.pimplant, prims.vthl), prims.nwell),
                ("nmos_vtg", prims.mosgate, (prims.nimplant, prims.vthg), prims.pwell),
                ("pmos_vtg", prims.mosgate, (prims.pimplant, prims.vthg), prims.nwell),
                ("nmos_vth", prims.mosgate, (prims.nimplant, prims.vthh), prims.pwell),
                ("pmos_vth", prims.mosgate, (prims.pimplant, prims.vthh), prims.nwell),
                ("nmos_thkox", prims.thkmosgate, prims.nimplant, prims.pwell),
                ("pmos_thkox", prims.thkmosgate, prims.pimplant, prims.nwell),
            )
        )

tech = technology = _FreePDK45()
