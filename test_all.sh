#!/bin/bash

mkdir -p output

for file in data/musdb18/test/*; do
  if [ -f "$file" ]; then
    python -m spleeter separate -o output/ -p configs/config.json "$file"
  fi
done
