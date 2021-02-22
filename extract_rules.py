#!/usr/bin/env python3
"""Script to extract the rules from PDK files"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
# Currently this is manual extraction for a signal TSMC 0.18um
# Plan is to update this is the future to make it generic and driven
# by an input file.

import yaml

from pdkmaster import AssuraContext

print("TSMC_CM018RF")

with open("tf_yaml/TSMC_CM018RF_TechFile.yaml") as f:
    tf = yaml.load(f, Loader=yaml.FullLoader)
with open("assura_yaml/TSMC_CM018RF_DRC.yaml") as f:
    drc = yaml.load(f, Loader=yaml.FullLoader)
with open("assura_yaml/TSMC_CM018RF_Antenna.yaml") as f:
    antenna = yaml.load(f, Loader=yaml.FullLoader)
# TODO: LVS and PEX

for expr in tf["TechFile"]:
    for key, value in expr.items():
        if key == "constraintGroups":
            tf_foundry = value["foundry"]

print("Techfile foundry constraints specified:")
for key in tf_foundry.keys():
    if key != "override":
        print("\t{}".format(key))


def _cond2str(expr):
    if isinstance(expr, list):
        return "("+" ".join(_cond2str(item) for item in expr)+")"
    elif isinstance(expr, dict):
        assert len(expr) == 1
        for key, args in expr.items():
            return key+_cond2str(args)
    else:
        return str(expr)

class AssuraDRC(dict):
    def extract_checks(self, value, *, condstr=""):
        for expr in value:
            if isinstance(expr, dict):
                for key, value in expr.items():
                    if key == "if":
                        condstr2 = _cond2str(value["cond"])
                        if len(condstr) > 0:
                            condstr2 = condstr+"&&"+condstr2
                        self.extract_checks(
                            value=value["then"]["statements"],
                            condstr=condstr2,
                        )
                        if "else" in value:
                            condstr2 = "!"+_cond2str(value["cond"])
                            if len(condstr) > 0:
                                condstr2 = condstr+"&&"+condstr2
                            self.extract_checks(
                                value=value["else"]["statements"],
                                condstr=condstr2,
                            )
                    elif key in ("drc", "errorLayer", "offGrid"):
                        self.add_check(condstr, key, value)

    def add_check(self, condstr, checktype, check):
        try:
            conddata = self[condstr]
        except KeyError:
            self[condstr] = conddata = {}

        try:
            conddata[checktype].append(check)
        except KeyError:
            conddata[checktype] = [check]

    def print_checks(self):
        keys = list(self.keys())
        keys.sort()

        for key in keys:
            print("{}:".format("Unconditioned" if key == "" else key))
            for checktype, checks in self[key].items():
                print("  {}:".format(checktype))
                for check in checks:
                    print("    {}".format(check))

    def get_sigs(self):
        sigs = {}
        for _, checktypes in self.items():
            for checktype, checks in checktypes.items():
                if checktype not in ("drc", "errorLayer", "offGrid"):
                    continue
                checksigs = set(tuple(type(expr) for expr in check) for check in checks)
                if checktype in sigs:
                    sigs[checktype].update(checksigs)
                else:
                    sigs[checktype] = checksigs

        return sigs

# assura_drc = AssuraDRC()
# for expr in drc["SkillFile"]:
#     if isinstance(expr, dict):
#         for key, value in expr.items():
#             if key == "drcExtractRules":
#                 assura_drc.extract_checks(value["statements"])

# #assura_drc.print_checks()
# print("drc signatures:")
# for checktype, sigs in assura_drc.get_sigs().items():
#     print("  {}:".format(checktype))
#     for sig in sigs:
#         print("    {}".format(sig))

context = AssuraContext()
ret = context.interpret(expr=drc["AssuraFile"], isstatements=True)

print("Assura DRC executed:")
print("  Returned: {}".format(ret))
print("  Procedures:")
for name in context.procedures:
    print("    {}".format(name))
print("  Variables:")
for name, value in context.variables.items():
    print("    {}: {}".format(name, value))
print("  Called: {}".format(context.called))
