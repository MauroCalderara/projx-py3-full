# Copyright __t_license_date__ __t_developer_name__
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provid with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# Some of the clunkiness here comes from the fact that at the time of this
# writing setuptools does not yet support pyproject.toml/PEP518/PEP621 so we
# use a bunch of helpers to fake that support. They populate the setup() 
# arguments with data parsed out of the pyproject.toml file. At some point
# one should be able to remove this glue code.

import collections
import io
import pathlib

from typing import Dict

import setuptools
import toml

class PyprojectTomlError(Exception):
    pass

def read_file(path: pathlib.Path) -> str:
    with io.open(path, encoding="utf8") as f:
        return f.read()

def pep51x_backport(pyproject_toml: pathlib.Path) -> Dict[str, str]:


    '''
    Parses project_root/pyproject.toml and extracts the fields specified in
    PEP518 into a dict suitable to be used as kwargs to setuptools.setup().
    This essentially constitutes a backport of PEP518 for the time setuptools
    does not yet support it officially.
    '''

    with io.open(pyproject_toml, encoding="utf8") as f:

        pyproject = toml.load(f)["project"]
        kwargs = dict()

        # name
        kwargs["name"] = pyproject["name"]

        # version
        kwargs["version"] = pyproject["version"]

        # description
        kwargs["description"] = pyproject["description"]

        # long_description / long_description_content_type
        readme_filename = pyproject["readme"]
        if readme_filename.endswith(".rst"):
            kwargs["long_description_content_type"] = "txt/x-rst"
        elif readme_filename.endswith(".md"):
            kwargs["long_description_content_type"] = "txt/markdown"
        else:
            kwargs["long_description_content_type"] = "txt/plain"
        kwargs["long_description"] = read_file(readme_filename)

        # python requires
        kwargs["python_requires"] = pyproject["requires-python"]

        # license
        license_x = pyproject["license"]
        if isinstance(license_x, collections.Mapping):
            if "file" not in license_x:
                raise PyprojectTomlError("Unsupported [project].license field")
            kwargs["license"] = read_file(license_x["file"])
        else:
            kwargs["license"] = license_x

        # Author(s) and maintainer(s) (this is a bit of a PITA because
        # setuptools does not support multiple authors officially so we convert
        # to "Some Name <some@email>, Other Name <other@email>").
        for tag in ["author", "maintainer"]:
            ts = pyproject[f"{tag}s"]
            if len(ts) == 1:
                kwargs[tag] = ts[0]["name"]
                kwargs[f"{tag}_email"] = ts[0]["email"]
            else:
                kwargs["tag"] = ", ".join([f"{t['name']} <t['email']>"
                                          for t in ts])

        # URLs
        kwargs["project_urls"] = pyproject["urls"]
        # We pick the first URL to be the project's main URL (this assumes an
        # ordered dict, which we have since python 3.6, i.e. the version we
        # explicitly require).
        kwargs["url"] = next(iter(pyproject["urls"].values()))

        # Dependencies
        kwargs["install_requires"] = pyproject["dependencies"]
        kwargs["extras_require"] = pyproject["optional_dependencies"]

        # This here is to allow setuptools to generate standalone scripts from
        # a so-called entry point. This is the modern way of making an
        # executable.
        kwargs["entry_points"] = dict()
        kwargs["entry_points"]["console_scripts"] = [
            f"{cli}={entry}" for cli, entry in pyproject["scripts"].items()
        ]

        # Classifiers
        kwargs["classifiers"] = pyproject["classifiers"]

        # Keywords
        kwargs["keywords"] = pyproject["keywords"]


if __name__ == "__main__":

    pyproject_root = pathlib.Path(__file__).parent.resolve()

    pyproject_cfg = pep51x_backport(pyproject_root / "pyproject.toml")

    setuptools.setup(

        # Note: most of the parameters are parsed out of pyproject.toml below.

        # This auto-detects all packages this code exposes, assuming the
        # structure is canonical.
        packages=setuptools.find_packages("src"),

        # Runnable from a zipped archive (.egg) since we don't parse our own
        # source. If we do, set this to False:
        zip_safe=True,

        # Everything else is parsed out of pyprojects.toml
        **pyproject_cfg

        # Other parameters that might be useful
        #
        # If you have a module named foo but it lives in src/bar:
        #package_dir={"foo": "src/bar"},
        #packages=["foo"]

        # If you have a module that lives in a single file e.g. a standalone
        # script (note that this refers to a module name so you have to omit the
        # .py suffix):
        #py_modules=["src/__t_module_name__/<standalon_script>"]

        # If you have any data that needs to be shipped with the package, see
        # package_data and [include,exclude]_package_data.

    )
