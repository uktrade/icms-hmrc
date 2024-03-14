#!/usr/bin/env bash

# Exit early if something goes wrong
set -e

# Add commands below to run as part of the pre_build phase

# Pipfile is not supported as an installation method
pipenv requirements > requirements.txt
rm -f Pipfile Pipfile.lock
