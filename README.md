# Description

PDK Master is a tool to manange foundry PDK for ASIC design.
It's mainly a work in progress.

# Copyright and licensing

git is used to track copyright of the code in this project.
Code in this repository is licensed under GNU General Public License v2.0 (see LICENSE) or later.

# Installation

_Unfinished_

Dependencies:

- modgrammar (available from pypi; automatically installed when using pip)
- shapely (available from pypi and conda; automatically installed when using pip)
- PySpice for simulation support  
  C4M extended version needed available on [Chips4Makers gitlab](https://gitlab.com/Chips4Makers/pyspice) (pull-requests pending on upstream repo for extensions):

```
        % git checkout https://gitlab.com/Chips4Makers/pyspice.git
        % cd pyspice
        % pip install .
```


- For the example notebooks:
    - Jupyter notebook capability: jupyter notebook, Jupyter lab, Visual Studio Code, ...  
      jupyter lab has nicer environment of class jupyter notebook
    - ipywidgets integration
