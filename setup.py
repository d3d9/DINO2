#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="DINO2-d3d9",
    version="1.0",
    author="Kevin Arutyunyan",
    author_email="d3d9@riseup.net",
    description="Process timetable data in the DINO 2.1 format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/d3d9/DINO2",
    packages=setuptools.find_packages(),
    install_requires=[
        "sqlalchemy",
        "pandas",
        "tqdm"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: OS Independent",
        "Topic :: Database",
    ],
    python_requires='>=3.7',
)