# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
import os, site
from pathlib import Path

from doit import get_var
from doit.tools import check_timestamp_unchanged, create_folder

### config


DOIT_CONFIG = {
    "default_tasks": ["install", "docs", "unittest"],
}


### support functions


def get_var_env(name, default=None):
    """Uses get_var to get a command line variable, also checks
    environment variables for default value

    If os.environ[name.upper()] exists that value will override the
    default value given.
    """
    try:
        default = os.environ[name.upper()]
    except:
        # Keep the specified default
        pass
    return get_var(name, default=default)


### globals


top_dir = Path(__file__).parent
docs_dir = top_dir.joinpath("docs")

# Don't use local module for pdkmaster
pdkmaster_inst_dir = Path(site.getsitepackages()[0]).joinpath("pdkmaster")
pdkmaster_local_dir = top_dir.joinpath("pdkmaster")
test_dir = top_dir.joinpath("test")

pip = get_var_env("pip", default="pip3")
sphinx_build = get_var_env("sphinx_build", default="sphinx-build")
coverage = get_var_env("coverage", default="coverage")

### main tasks


#
# install
pdkmaster_py_files = tuple(pdkmaster_local_dir.rglob("*.py"))
def task_install():
    """Install the pyhton module"""

    return {
        "title": lambda _: "Installing python module",
        "file_dep": (top_dir.joinpath("setup.py"), *pdkmaster_py_files),
        "targets": (pdkmaster_inst_dir,),
        "actions": (f"{pip} install {top_dir}",),
    }


#
# docs
def task_docs():
    """Create the documentation with Sphinx"""

    docs_src_dir = docs_dir.joinpath("src")
    docs_html_dir = docs_dir.joinpath("html")

    docs_rst_files = tuple(docs_src_dir.rglob("*.rst"))
    docs_html_files = tuple(
        docs_html_dir.joinpath(f.name.replace(".rst", ".html"))
        for f in docs_rst_files
    )
    docs_html_dir = docs_dir.joinpath("html")

    return {
        "title": lambda _: "Creating the documentation",
        "file_dep": (
            *docs_rst_files,
            docs_src_dir.joinpath("conf.py"),
        ),
        "uptodate": (
            check_timestamp_unchanged(str(pdkmaster_inst_dir)),
        ),
        "task_dep": ("install",),
        "targets": docs_html_files,
        "actions": (
            (create_folder, (docs_html_dir,)),
            f"{sphinx_build} -b html {docs_src_dir} {docs_html_dir}",
        )
    }

#
# test
test_py_files = tuple(test_dir.rglob("*.py"))
test_report_file = test_dir.joinpath("cover_report.log")
def task_unittest():
    """Run unittests with and coverage"""

    return {
        "title": lambda _: "Running unittests and coverage",
        "file_dep": (*pdkmaster_py_files, *test_py_files),
        "targets": (test_report_file,),
        "actions": (
            f"{coverage} run --include 'pdkmaster/*' -m unittest discover -s test -p '*.py'",
            f"{coverage} report -m | tee {test_report_file}",
            f"grep 'TOTAL' {test_report_file} 1>&2"
        )
    }