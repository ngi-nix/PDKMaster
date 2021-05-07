# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
"""
Coding conventions
------------------

* Classes of which no object are supposed to be created in user code start with
  an underscore. Typically this means that the object should typically be generated
  from a Factory or other object that can generate this object. It thus typically
  means that no backwards guarantee is given for the __init__() method of the class.
* functions, object methods and attributes starting with an underscore are for internal
  use only. No backwards guarantee is given and they may be changed or removed.
"""
__path__ = __import__('pkgutil').extend_path(__path__, __name__)
