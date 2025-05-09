#!/bin/bash

# Gateway script

SCRIPT_PATH="$HOME/path/to/project_folder"

# Run script with any additional arguments passed to this script
"$SCRIPT_PATH/venv/bin/python3" "$SCRIPT_PATH/main.py" "$@"