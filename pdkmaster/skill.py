#!/bin/env python3
"""Python code for parsing a Cadence technology file"""
import sys
import yaml

import skill_grammar
import modgrammar.debugging

# Override debug
skill_grammar._debug = True

with open(sys.argv[1], "r", encoding="latin_1") as f:
    text = f.read()

debug = None
debug_flags = None
# debug = True
# debug_flags = modgrammar.debugging.DEBUG_ALL
p = skill_grammar.SkillFile.parser(debug=debug, debug_flags=debug_flags)
skillfile = p.parse_string(text)

# for it in skillfile.value["SkillFile"]:
#     for name, _ in it.items():
#         print(name)
if len(sys.argv) > 2:
    with open(sys.argv[2], "w") as f:
        yaml.dump(skillfile.ast, stream=f, sort_keys=False)
else:
    yaml.dump(skillfile.ast, stream=sys.stdout, sort_keys=False)
