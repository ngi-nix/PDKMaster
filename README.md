# Description

PDK Master is a tool to manange foundry PDK for ASIC design and a framework for designing circuits and layouts in those technologies.
It's mainly a work in progress.

# Installation

_Unfinished_

Dependencies:

- modgrammar (available from pypi; automatically installed when using pip)
- shapely (available from pypi and conda; automatically installed when using pip)
- descartes (available from pypi and conda; automatically installed when using pip)
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
    - ipywidgets integration, likely node.js also needed for ipywidgets integration in jupyter lab.

# Copyright and licensing

git is used to track copyright of the code in this project.
Code in this repository is multi-licensed, see [LICENSE.md](LICENSE.md) for details.
