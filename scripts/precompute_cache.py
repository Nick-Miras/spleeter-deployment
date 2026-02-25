import tensorflow as tf
from spleeter.utils.configuration import load_configuration
from spleeter.dataset import DatasetBuilder
from spleeter.audio.adapter import AudioAdapter

# 1. Load your configuration
config = load_configuration("configs/modified_config.json")
audio_adapter = AudioAdapter.default()

# 2. Initialize the Dataset Builder
# Note: Adjust 'audio_path' to point to your root dataset directory
builder = DatasetBuilder(
    config, 
    audio_adapter, 
    audio_path="data/Datasets"
)

# 3. Build the dataset pipeline
train_dataset = builder.build(
    config["train_csv"], 
    cache_directory=config["training_cache"]
)

# 4. Iterate to force the CPU to compute STFTs and write the cache
print("Caching training data... This will maximize your CPU usage.")
for i, batch in enumerate(train_dataset):
    if i % 50 == 0:
        print(f"Processed {i} chunks...")
        
print("Training cache successfully written to disk!")