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
config['train_csv'] = os.path.join(root, 'data', 'train.csv')
config['validation_csv'] = os.path.join(root, 'data', 'val.csv')
config['model_dir'] = os.path.join(root, 'training_output')

with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

print(f'Updated {config_path} with project root: {root}')
"
