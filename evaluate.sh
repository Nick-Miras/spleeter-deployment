#!/bin/bash
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

wget https://zenodo.org/records/1117372/files/musdb18.zip?download=1 -O musdb18.zip
mkdir data/musdb18
unzip musdb18.zip -d data/musdb18/
rm musdb18.zip

hf download NickAnthonyMiras/spleeter-thesis-1.514m --repo-type model --local-dir spleeter_pretrained1/

python create_paths.py
python scripts/evaluate.py \
    --model configs/modified_config.json \
    --out metrics.csv \
    --stem-names drums bass other vocals \
    --dataset data/musdb18/test/ \
    --stem-mp4-batch
