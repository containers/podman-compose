# SPDX-License-Identifier: GPL-2.0

import os

from setuptools import setup

try:
    README = open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8").read()
except:  # noqa: E722 # pylint: disable=bare-except
    README = ""

setup(
    name="podman-compose",
    description="A script to run docker-compose.yml using podman",
    long_description=README,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords="podman, podman-compose",
    author="Muayyad Alsadi",
    author_email="alsadi@gmail.com",
    url="https://github.com/containers/podman-compose",
    py_modules=["podman_compose"],
    entry_points={"console_scripts": ["podman-compose = podman_compose:main"]},
    include_package_data=True,
    license="GPL-2.0-only",
    install_requires=[
        "pyyaml",
        "python-dotenv",
    ],
    extras_require={"devel": ["ruff", "pre-commit", "coverage", "parameterized"]},
    # test_suite='tests',
    # tests_require=[
    #     'coverage',
    #     'tox',
    # ]
)
