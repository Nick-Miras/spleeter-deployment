import json
import os

config_path = 'configs/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)

root = os.getcwd()
config['train_csv'] = os.path.join(root, 'data', 'train_unix.csv')
config['validation_csv'] = os.path.join(root, 'data', 'validation_unix.csv')
config['model_dir'] = os.path.join(root, 'spleeter_pretrained1')

with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)

print(f'Updated {config_path} with project root: {root}')