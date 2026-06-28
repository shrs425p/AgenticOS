#!/bin/bash
export PYTHONPATH=.
mkdir -p manuals
pydoc-markdown > manuals/api.md
