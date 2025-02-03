#!/bin/bash
# Path where the output will be saved
OUTPUT_FILE="/tmp/smbstatus_output.txt"
# Run smbstatus and save output to file
sudo smbstatus > "$OUTPUT_FILE"