# SPDX-License-Identifier: GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+
from setuptools import setup, find_packages


def scm_version():
    def local_scheme(version):
        if version.tag and not version.distance:
            return version.format_with("")
        else:
            return version.format_choice("+{node}", "+{node}.dirty")
    return {
        "relative_to": __file__,
        "version_scheme": "guess-next-dev",
        "local_scheme": local_scheme
    }

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="PDKMaster",
    use_scm_version=scm_version(),
    author="Staf Verhaegen",
    author_email="staf@fibraservi.eu",
    description="ASIC PDK Manager and Design Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="GPL-2.0-or-later OR AGPL-3.0-or-later OR CERN-OHL-S-2.0+",
    python_requires="~=3.6",
    setup_requires=["setuptools_scm"],
    install_requires=[
        "setuptools", "modgrammar", "shapely", "descartes",
        "c4m-PySpice~=1.4.3.post0",
    ],
    include_package_data=True,
    packages=find_packages(),
    project_urls={
        #"Documentation": "???",
        "Source Code": "https://gitlab.com/Chips4Makers/PDKMaster",
        "Bug Tracker": "https://gitlab.com/Chips4Makers/PDKMaster/issues",
    },
)
