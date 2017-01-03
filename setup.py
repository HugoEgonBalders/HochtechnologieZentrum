#! /usr/bin/env python3
import os
import importlib.machinery

import setuptools


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VERSION_FILE_PATH = os.path.join(BASE_DIR, 'aiml/_version.py')
print(VERSION_FILE_PATH)
module_loader = importlib.machinery.SourceFileLoader("aiml._version", VERSION_FILE_PATH)
version = module_loader.load_module().__version__

setuptools.setup(
    name="PyAIML",
    version=version,
    author="Cort Stratton",
    description="An interpreter package for AIML, the Artificial Intelligence Markup Language",
    long_description="""PyAIML implements an interpreter for AIML, the Artificial Intelligence
Markup Language developed by Dr. Richard Wallace of the A.L.I.C.E. Foundation.
It can be used to implement a conversational AI program.""",
    url="https://github.com/warvariuc/pyaiml",
    platforms=["any"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        'License :: OSI Approved :: BSD License',
        "Topic :: Communications :: Chat",
        "Topic :: Scientific/Engineering :: Artificial Intelligence"
    ],
    packages=["aiml"],
    include_package_data=True,  # use MANIFEST.in during install
)
