export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

python -m spleeter train -p configs/config.json -d data/

cd /home/ubuntu
FILE_NAME=model_weights_$(date +%Y%m%d_%H%M)
zip -r "$FILE_NAME.zip" $WORKING_DIR/thesis/spleeter_pretrained1/

# sudo shutdown -h +1
