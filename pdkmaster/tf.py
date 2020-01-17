#!/bin/env python3
"""Python code for parsing a Cadence technology file"""
import sys
import yaml

from tf_grammar import *

with open(sys.argv[1], "r", encoding="latin_1") as f:
    text = f.read()

techfile = TechFile.parser().parse_string(text)

for it in techfile.value["TechFile"]:
    for name, _ in it.items():
        print(name)


