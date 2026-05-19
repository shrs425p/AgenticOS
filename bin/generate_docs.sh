#!/bin/bash
export PYTHONPATH=.
mkdir -p docs
pydoc-markdown > docs/api_reference.md
