#!/usr/bin/env python3
"""Convert all the SKILL files to yaml files"""
# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import yaml

from files import techfiles, assurafiles, ilfiles, displayfiles
from pdkmaster.io.parsing import SkillFile, TechFile, AssuraFile, DisplayFile

# techfiles
for techfile, yamlfile in techfiles:
    print("Converting -> "+yamlfile)
    with open(techfile, "r", encoding="latin1") as f:
        text = f.read()

    tf = TechFile.parse_string(text)

    with open("tf_yaml/"+yamlfile, "w") as f:
        yaml.dump(tf.value, f, sort_keys=False)

# assurafiles
for assurafile, yamlfile in assurafiles:
    print("Converting -> "+yamlfile)
    with open(assurafile, "r", encoding="latin1") as f:
        text = f.read()

    assf = AssuraFile.parse_string(text)

    with open("assura_yaml/"+yamlfile, "w") as f:
        yaml.dump(assf.value, f, sort_keys=False)

# displayfiles
for displayfile, yamlfile in displayfiles:
    print("Converting -> "+yamlfile)
    with open(displayfile, "r", encoding="latin1") as f:
        text = f.read()

    dispf = DisplayFile.parse_string(text)

    with open("display_yaml/"+yamlfile, "w") as f:
        yaml.dump(dispf.value, f, sort_keys=False)

# TODO ilfiles
