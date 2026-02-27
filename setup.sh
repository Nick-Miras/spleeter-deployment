# Create directory structure
PROJECT_ROOT=$(pwd)
mkdir -p data/Datasets
cd data
# Download the dataset
hf download qrowraven/Datasetqrow --repo-type dataset --local-dir Datasets


# Update config paths
cd "$PROJECT_ROOT"
python3 -c "
import json
import os

config_path = 'configs/modified_config.json'
with open(config_path, 'r') as f:
    config = json.load(f)

root = os.getcwd()
config['train_csv'] = os.path.join(root, 'data', 'train_unix.csv')
config['validation_csv'] = os.path.join(root, 'data', 'validation_unix.csv')
config['model_dir'] = os.path.join(root, 'spleeter_pretrained1')

with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

print(f'Updated {config_path} with project root: {root}')
"


# Download pretrained model
echo "Downloading pretrained model..."
mkdir -p spleeter_pretrained1
cd spleeter_pretrained1
wget https://github.com/deezer/spleeter/releases/download/v1.4.0/4stems-finetune.tar.gz
tar -xzf 4stems-finetune.tar.gz
rm 4stems-finetune.tar.gz

echo "Setup complete. You can now run 'train.sh' to start training and 'monitor.sh' to monitor with TensorBoard."
