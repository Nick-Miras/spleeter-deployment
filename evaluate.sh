#!/bin/bash
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
wget https://zenodo.org/records/1117372/files/musdb18.zip
unzip musdb18.zip -d data/
rm musdb18.zip

hf download NickAnthonyMiras/spleeter-thesis-1.514m --repo-type model --local-dir spleeter_pretrained1/

python scripts/custom_evaluate.py --config configs/modified_config.json --dataset_dir data
