#!/bin/env python3
from files import techfiles, assurafiles, ilfiles, displayfiles
from pdkmaster.io.parsing import SkillFile

ilfiles2 = tuple((ilfile, "ilfile"+str(i)) for i, ilfile in enumerate(ilfiles))

all_files = techfiles + assurafiles + ilfiles2 + displayfiles
for skillfile, yamlfile in all_files:
    print("Checking for "+yamlfile)

    with open(skillfile, "r", encoding="latin_1") as f:
        text = f.read()

    # Just check is parsing works
    SkillFile.parse_string(text)
