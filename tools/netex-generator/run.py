"""Launcher for `python -I run.py <module> [args]`.

Isolated mode (-I) ignores the current directory and PYTHONPATH, so a planted
module in a download directory cannot be imported. This file adds only its own
directory (the generators' code) to sys.path.
"""
import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
module = sys.argv[1]
sys.argv = [module] + sys.argv[2:]
runpy.run_module(module, run_name="__main__", alter_sys=True)
