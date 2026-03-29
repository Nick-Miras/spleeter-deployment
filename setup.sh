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
hf download NickAnthonyMiras/spleeter-thesis-1.514m --repo-type model --local-dir .

echo "Setup complete. You can now run 'train.sh' to start training and 'monitor.sh' to monitor with TensorBoard."
