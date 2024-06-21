"""Setup config for the module."""

# pylint: disable=E0401,E0611

from distutils.core import setup  # pyright: ignore [reportMissingImports]

setup(
    setup_requires=["wheel"],
    url="https://ortelius.io",
    project_urls={
        "Project Repo": "https://github.com/ortelius/ortelius-cli",
        "Issues": "https://github.com/ortelius/ortelius/issues",
        "Ortelius CLI Documentation": "https://github.com/ortelius/ortelius-cli/blob/main/doc/dh.md",
        "Python Python API Documentation": "https://github.com/ortelius/ortelius-cli/blob/main/doc/deployhub.md",
    },
    author="Steve Taylor",
    author_email="steve@deployhub.com",
    name="ortelius-cli",
    version="9.3.277",
    packages=[
        "deployhub",
    ],
    scripts=["bin/dh"],
    license="Apache-2.0",
    long_description=open("doc/dh.md").read(),
    long_description_content_type="text/markdown",
    python_requires=">=3.6",
    install_requires=["click", "qtoml", "pyyaml", "requests", "configobj", "flatten_dict", "pydantic", "certifi"],
    include_package_data=True,
)
