#!/bin/bash

# Check if a file was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <filename.csv>"
    exit 1
fi

input_file="$1"
# Create an output filename (e.g., data.csv becomes data_unix.csv)
output_file="${input_file%.*}_unix.csv"

# Perform the translation
tr '\\' '/' < "$input_file" > "$output_file"

echo "Success! Converted paths saved to: $output_file"