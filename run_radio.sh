#!/bin/bash

# Save the current directory
CURRENT_DIR=$(pwd)

# Navigate to the desired directory
cd "/home/azzar/Downloads/project/terminal radio/" || exit

# Run the Python script
python radio.py

# Return to the original directory
cd "$CURRENT_DIR"
