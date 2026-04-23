# Create directory structure
PROJECT_ROOT=$(pwd)
mkdir -p data/Datasets
# Download the dataset
aws s3 sync s3://spleeter-dataset-338310096867-us-east-1-an data/Datasets

# Update config paths
cd "$PROJECT_ROOT"
python3 scripts/write_paths.py

# Download precomputed cache
echo "Downloading precomputed cache..."
aws s3 sync s3://spleeter-cache-338310096867-us-east-1-an cache/

# Download pretrained model
echo "Downloading pretrained model..."
mkdir -p spleeter_pretrained1
cd spleeter_pretrained1
wget https://github.com/deezer/spleeter/releases/download/v1.4.0/4stems-finetune.tar.gz
tar -xzf 4stems-finetune.tar.gz
rm 4stems-finetune.tar.gz

echo "Setup complete. You can now run 'train.sh' to start training and 'monitor.sh' to monitor with TensorBoard."
