from .. import technology as tech, layer, device as dev

__all__ = ["technology"]

class _FreePDK45(tech.Technology):
    def __init__(self):
        super().__init__("FreePDK45")

        self.constraints += (self.grid == 0.0025)

        # Wiki: Layers
        self.layers += [layer.Layer(name) for name in [
            "active", "nwell", "pwell", "nimplant", "pimplant", "sblock",
            "vthl", "vthg", "vthh", "thkox", "poly", "contact",
            "metal1", "via1", "metal2", "via2", "metal3", "via3", "metal4", "via4", "metal5", "via5",
            "metal6", "via6", "metal7", "via7", "metal8", "via8", "metal9", "via9", "metal10",
        ]]
        lrs = self.layers

        wells = [lrs.nwell, lrs.pwell]
        transimplants = [lrs.nimplant, lrs.pimplant]
        
        # TODO: same net rules
        # TODO: layer needs to be covered by other layer
        # TODO: assymetric enclosure of contact/vias
        # TODO: Find out what Implant.2 is supposed to mean
        #       ""
        # TODO: Find out what MetalTNG.4 is supposed to mean
        #       "Minimum area of metalTNG straddling via[6-8]"
        self.constraints += [
            # Wiki: Poly Rules
            lrs.poly.width >= 0.050, # Poly.1
            # Poly.2 => transistor rule,
            lrs.poly.extend_over(lrs.active) >= 0.055, # Poly.3
            lrs.active.extend_over(lrs.poly) >= 0.070, # Poly.4
            lrs.poly.space_to(lrs.active) >= 0.050, # Poly.5
            lrs.poly.space >= 0.075, # Poly.6

            # Wiki: Well Rules
            lrs.nwell.overlap_with(lrs.pwell) <= 0.000, # Well.1
            #*[well.space_to(well.other_net) >= 0.225]], # Well.2
            #*[well.space_to(well.same_net) >= 0.135]], # Well.3
            *[well.space >= 0.225 for well in wells], # Well.2+3
            *[well.width >= 0.200 for well in wells], # Well.4

            # Wiki: Implant Rules
            # Implant.1 => transistor rule
            # ??? Implant.2
            *[implant.width >= 0.045 for implant in transimplants], # Implant.3
            *[implant.space >= 0.045 for implant in transimplants], # Implant.4
            lrs.nimplant.overlap_with(lrs.pimplant) <= 0.000, # Implant.5

            # Wiki: Active Rules
            lrs.active.width >= 0.090, # Active.1
            lrs.active.space >= 0.080, # Active.2
            *[lrs.active.enclosed_by(well) >= 0.055 for well in wells], # Active.3
            *[lrs.active.space_to(well) >= 0.055 for well in wells], # Active.3
            lrs.active.is_inside(wells), # Active.4

            # Wiki: Contact Rules
            lrs.contact.width == 0.065, # Contact.1
            lrs.contact.space >= 0.075, # Contact.2
            lrs.contact.is_inside(lrs.active, lrs.poly), # Contact.3
            lrs.contact.is_inside(lrs.metal1), # Contact.3
            lrs.contact.enclosed_by(lrs.active) >= 0.005, # Contact.4
            lrs.contact.enclosed_by(lrs.poly) >= 0.005, # Contact.5
            # Contact.6 => transistor rule
            lrs.contact.space_to(lrs.poly) >= 0.090, # Contact.7

            # Wiki Metal1 Rules
            lrs.metal1.width >= 0.065, # Metal1.1
            lrs.metal1.space >= 0.065, # Metal1.2
            #contact.enclosed_by(metal1) >= (0.000, 0.035), # Metal1.3
            #via1.enclosed_by(metal1) >= (0.000, 0.035), # Metal1.4
            # Metal1.5-9 => space tables

            # Wiki: Via1 Rules
            lrs.via1.width == 0.065, # Via1.1
            lrs.via1.space >= 0.075, # Via1.2
            lrs.via1.is_inside(lrs.metal1), # Via1.3
            lrs.via1.is_inside(lrs.metal2), # Via1.4

            # Wiki: MetalInt Rules
            lrs.metal2.width >= 0.070, # MetalInt.1
            lrs.metal3.width >= 0.070, # MetalInt.1
            lrs.metal2.space >= 0.070, # MetalInt.2
            lrs.metal3.space >= 0.070, # MetalInt.2
            #via1.enclosed_by(metal2) >= (0.000, 0.035), # MetalInt.3
            #via2.enclosed_by(metal2) >= (0.000, 0.035), # MetalInt.4
            #via2.enclosed_by(metal3) >= (0.000, 0.035), # MetalInt.4
            #via3.enclosed_by(metal3) >= (0.000, 0.035), # MetalInt.4
            # MetalInt.5-9 => space tables

            # Wiki: Via23 Rules
            lrs.via2.width == 0.070, # Via[2-3].1
            lrs.via3.width == 0.070, # Via[2-3].1
            lrs.via2.space >= 0.085, # Via[2-3].2
            lrs.via3.space >= 0.085, # Via[2-3].2
            lrs.via2.is_inside(lrs.metal2), # Via[2-3].3
            lrs.via3.is_inside(lrs.metal3), # Via[2-3].3
            lrs.via2.is_inside(lrs.metal3), # Via[2-3].4
            lrs.via3.is_inside(lrs.metal4), # Via[2-3].4

            # Wiki: MetalSMG Rules
            lrs.metal4.width >= 0.140, # MetalSMG.1
            lrs.metal5.width >= 0.140, # MetalSMG.1
            lrs.metal6.width >= 0.140, # MetalSMG.1
            lrs.metal4.space >= 0.140, # MetalSMG.2
            lrs.metal5.space >= 0.140, # MetalSMG.2
            lrs.metal6.space >= 0.140, # MetalSMG.2
            # MetalSMG.3 => is_inside rule
            # MetalSMG.6-8 => space tables

            # Wiki: Via46 Rules
            lrs.via4.width == 0.140, # Via[4-6].1
            lrs.via5.width == 0.140, # Via[4-6].1
            lrs.via6.width == 0.140, # Via[4-6].1
            lrs.via4.space >= 0.160, # Via[4-6].2
            lrs.via5.space >= 0.160, # Via[4-6].2
            lrs.via6.space >= 0.160, # Via[4-6].2
            lrs.via4.is_inside(lrs.metal4), # Via[4-6].3
            lrs.via5.is_inside(lrs.metal5), # Via[4-6].3
            lrs.via6.is_inside(lrs.metal6), # Via[4-6].3
            lrs.via4.is_inside(lrs.metal5), # Via[4-6].4
            lrs.via5.is_inside(lrs.metal6), # Via[4-6].4
            lrs.via6.is_inside(lrs.metal7), # Via[4-6].4

            # Wiki: MetalTNG Rules
            lrs.metal7.width >= 0.400, # MetalTNG.1
            lrs.metal8.width >= 0.400, # MetalTNG.1
            lrs.metal7.space >= 0.400, # MetalTNG.2
            lrs.metal8.space >= 0.400, # MetalTNG.2
            # MetalTNG.3 => is_inside rule
            # ??? MetalTNG.4
            # MetalTNG.5-6 => don't seem to make sense

            # Wiki: Via78 Rules
            lrs.via7.width == 0.400, # Via[7-8].1
            lrs.via8.width == 0.400, # Via[7-8].1
            lrs.via7.space >= 0.440, # Via[7-8].2
            lrs.via8.space >= 0.440, # Via[7-8].2
            lrs.via7.is_inside(lrs.metal7), # Via[7-8].3
            lrs.via8.is_inside(lrs.metal8), # Via[7-8].3
            lrs.via7.is_inside(lrs.metal8), # Via[7-8].4
            lrs.via8.is_inside(lrs.metal9), # Via[7-8].4

            # Wiki: MetalG Rules
            lrs.metal9.width >= 0.800, # MetalG.1
            lrs.metal10.width >= 0.800, # MetalG.1
            lrs.metal9.space >= 0.800, # MetalG.2
            lrs.metal10.space >= 0.800, # MetalG.2
            # MetalTNG.3 => is_inside rule
            # MetalG.8-9 => space tables

            # Wiki: Via8 Rules
            lrs.via9.width == 0.800, # Via[9].1
            lrs.via9.space >= 0.880, # Via[9].2
            lrs.via9.is_inside(lrs.metal9), # Via[9].3
            lrs.via9.is_inside(lrs.metal10), # Via[9].4
        ]

        # Space Tables
        # TODO: spacing as function of width/length
        # Made tables more consistent than in the wiki pages.
        # for layers, space_table in [
        #     ((lrs.metal1, lrs.metal2, lrs.metal3), (
        #         (0.090, 0.900, 0.090), # Metal1.5/MetalInt.5
        #         (0.270, 0.300, 0.270), # Metal1.6/MetalInt.6
        #         (0.500, 1.800, 0.500), # Metal1.7/MetalInt.7
        #         (0.900, 2.700, 0.900), # Metal1.8/MetalInt.8
        #         (1.500, 4.000, 1.500), # Metal1.9/MetalInt.9
        #     )),
        #     ((lrs.metal4, lrs.metal5, lrs.metal6), (
        #         (0.270, 0.300, 0.270), # MetalSMG.6
        #         (0.500, 1.800, 0.500), # MetalSMG.7
        #         (0.900, 2.700, 0.900), # MetalSMG.8
        #         (1.500, 4.000, 1.500), # MetalSMG.9; added
        #     )),
        #     ((lrs.metal7, lrs.metal8), (
        #         # MetalTNG.5-6 ignored
        #         (0.500, 1.800, 0.500), # MetalSMG.7; added
        #         (0.900, 2.700, 0.900), # MetalSMG.8; added
        #         (1.500, 4.000, 1.500), # MetalSMG.9; added
        #     )),
        #     ((lrs.metal9, lrs.metal10), (
        #         (0.900, 2.700, 0.900), # MetalG.8
        #         (1.500, 4.000, 1.500), # MetalG.9
        #     )),
        # ]:
        #     for lay in layers:            
        #         self.constraints += [
        #             lay.select(metal1.width >= width, metal1.length >= length).space_to(lay) >= space
        #             for width, length, space in space_table
        #         ]

        mosfets = [
            dev.MOSFET("nmos_vtl",
                poly=lrs.poly, active=lrs.active, implant=(lrs.nimplant, lrs.vthl), well=lrs.pwell,
            ),
            dev.MOSFET("pmos_vtl",
                poly=lrs.poly, active=lrs.active, implant=(lrs.pimplant, lrs.vthl), well=lrs.nwell
            ),
            dev.MOSFET("nmos_vtg",
                poly=lrs.poly, active=lrs.active, implant=(lrs.nimplant, lrs.vthg), well=lrs.pwell,
            ),
            dev.MOSFET("pmos_vtg",
                poly=lrs.poly, active=lrs.active, implant=(lrs.pimplant, lrs.vthg), well=lrs.nwell
            ),
            dev.MOSFET("nmos_vth",
                poly=lrs.poly, active=lrs.active, implant=(lrs.nimplant, lrs.vthh), well=lrs.pwell,
            ),
            dev.MOSFET("pmos_vth",
                poly=lrs.poly, active=lrs.active, implant=(lrs.pimplant, lrs.vthh), well=lrs.nwell
            ),
            dev.MOSFET("nmos_thkox",
                poly=lrs.poly, active=lrs.active, implant=(lrs.nimplant, lrs.thkox), well=lrs.pwell,
            ),
            dev.MOSFET("pmos_thkox",
                poly=lrs.poly, active=lrs.active, implant=(lrs.pimplant, lrs.thkox), well=lrs.nwell
            ),
        ]
        self.devices += mosfets
        for trans in mosfets:
            try:
                implant = trans.implant[0]
            except TypeError:
                implant = trans.implant

            # Transistor Rules
            self.constraints += [
                trans.l >= 0.050, trans.w >= 0.090,
                trans.gate.space >= 0.140, # Poly.2
                trans.gate.enclosed_by(implant) >= 0.078, # Implant.1
                lrs.contact.is_outside(trans.gate), # Implicit
                trans.gate.space_to(lrs.contact) >= 0.035, # Contact.6
            ]
        
technology = _FreePDK45()
