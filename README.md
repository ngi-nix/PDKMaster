# Description

PDK Master is a tool to manage [PDK](https://en.wikipedia.org/wiki/Process_design_kit)s for ASIC design and a framework for designing circuits and layouts in those technologies.
It is a Python framework under heavy development and with an unstable API.

# Overview

Currently no documentation is available, the documentation is planned to be added as part of the stabilization of the PDKMaster API. To show the things PDKMaster wants to solve here an overview of the different parts of the current PDKMaster code base:

* pdkmaster: the top python module
  * `_util.py`: some helper functions and classes
  * technology:
  this submodule handles the description of an ASIC technology with final target to allow describe that in one python file.
    * `property_.py`: base class to represent properties on operations that can be done on them.
    * `rule.py`: abstract base class to represent a rule object, e.g. a condition on properties that has to be fulfilled to be manufacturable.
    * `mask.py`: class to represent the photolithography masks used in ASIC production and the properties on them. The latter are then used to define design rules.
    * `edge.py`: class representing mask edges and it's properties to be used in design rules.
    * `wafer.py`: object to represent a (silicon) wafer that is the start of processing and that is auto-connected to some device ports.
    * `net.py`: class representing a net, e.g. o group of conductors in a circuit that are connected together.
    * `primitive.py`: classes for all possible device primitives available in a technology. This goes from low-level interconnect to transistors. As indication of the content here the exported classes are given:
      ```python
      __all__ = ["Marker", "Auxiliary", "ExtraProcess",
                 "Implant", "Well",
                 "Insulator", "WaferWire", "GateWire", "MetalWire", "TopMetalWire",
                 "Via", "PadOpening",
                 "Resistor", "Diode",
                 "MOSFETGate", "MOSFET",
                 "Spacing",
                 "UnusedPrimitiveError", "UnconnectedPrimitiveError"]
      ```
      The object attibutes defined by these classes are used to derive mask design rules.
    * `dispatcher.py`: helper class to allow primitive iteration code inspired by the [Visitor design pattern](https://en.wikipedia.org/wiki/Visitor_pattern).
    * `technology_.py`: class to define the capability of a certain technology: all support devices, the masks needed to define them and the rules for making circuit in this technology.
  * design: support code for making circuits compliant with a given technology.
    * `circuit.py`: defines a factory that allows to generate objects of the Circuit class using devices from a given technology.
    * `layout.py`: classes to define layout compliant with a given technology and a factory to generate layouts for a given circuit that are technology design rule compliant.
    * `library.py`: contains:
      * Cell class: representing several possible circuit representations and layouts of a block with the same function
      * Library class: represent a collections of cells
  * io: submodule to import and export technology data
    * parsing: submodule to parse setup files for other EDA tools and extract data to build a PDKMaster technology object based on this data.
      * `skill_grammar.py`: modgrammar based parser for [SKILL](https://en.wikipedia.org/wiki/Cadence_SKILL)(-like) files. [SKILL](https://en.wikipedia.org/wiki/Cadence_SKILL) is the Cadence bastardized version of [Lisp](https://en.wikipedia.org/wiki/Lisp_(programming_language)).
      * `tf.py`, `display.py`, `layermap.py`, `assura.py`: classes for representing Cadence EDA files based on the [SKILL](https://en.wikipedia.org/wiki/Cadence_SKILL) grammar.
    * export:
      * `pdkmaster.py`: support code to export a PDKMaster technology as Python souce code; main targeted use case to use the parsing submodule to extract data from NDA covered PDK and generate PDKMaster Technology object without needing to disctribute NDA covered data.
      * `coriolis.py`: support code to generate Coriolis technology setup, cells and libraries from PDKMaster objects.
      * `klayout.py`: support code to generate klayout Technology setup for PDKMaster Technology object including DRC and LVS scripts.
      * `pyspice.py`: support code to convert PDKMaster Circuit to PySpice Circuits to be used in simulation.

The current code base has been gradually grown to allow to do a 0.18µm prototype layout of the NLNet sponsored Libre-SOC project. It has known (and unknown) inconsistencies and shortcomings. A full revision of the current API is planned without any backwards guarantees whatsoever. As this is an open source project it is meant to be used by other people but one should be aware that user code using PDKMaster has a high chance of breaking with each commit done to the repository in the near future.

# Installation

All dependencies for installation should be available so PDKMaster should be able to installed by a simple pip command.

```console
% pip install PDKMaster
```

More in depth discussion of different `pip` use case scenarios is out of the scope of this document.

Dependencies:

- [modgrammar](https://pythonhosted.org/modgrammar/)
- [shapely](https://shapely.readthedocs.io/en/latest/manual.html), [descartes](https://pypi.org/project/descartes/) (used for internal representation of layouts, planned to be replaced with using the klayout python API)
- [c4m-PySpice](https://gitlab.com/Chips4Makers/c4m-PySpice) (this a fork of PySpice with additional patches from PRs applied)

# Copyright and licensing

git is used to track copyright of the code in this project.
Code in this repository is multi-licensed, see [LICENSE.md](LICENSE.md) for details.
