export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

python -m spleeter train -p configs/modified_config.json -d data/

zip -r model_weights.zip spleeter_pretrained1/
