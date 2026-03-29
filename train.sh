export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

python -m spleeter train -p configs/config.json -d data/

FILE_NAME=model_weights_$(date +%Y%m%d_%H%M)
zip -r "$FILE_NAME.zip" spleeter_pretrained1/

cp "$FILE_NAME.zip" /home/ubuntu/

# sudo shutdown -h +1
