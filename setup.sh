# Create directory structure
PROJECT_ROOT=$(pwd)
mkdir -p data/Datasets
cd data
# Download the dataset
hf download qrowraven/Datasetqrow --repo-type dataset --local-dir Datasets


# Update config paths
cd "$PROJECT_ROOT"
python3 convert_paths.py


# Download pretrained model
echo "Downloading pretrained model..."
mkdir -p spleeter_pretrained1
cd spleeter_pretrained1
wget https://github.com/deezer/spleeter/releases/download/v1.4.0/4stems-finetune.tar.gz
tar -xzf 4stems-finetune.tar.gz
rm 4stems-finetune.tar.gz

echo "Setup complete. You can now run 'train.sh' to start training and 'monitor.sh' to monitor with TensorBoard."
