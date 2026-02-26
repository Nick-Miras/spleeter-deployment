import tensorflow as tf
from spleeter.utils.configuration import load_configuration
from spleeter.dataset import DatasetBuilder
from spleeter.audio.adapter import AudioAdapter
import tqdm
import math


config = load_configuration("configs/modified_config.json")
audio_adapter = AudioAdapter.default()

# Make sure your batch_size is set high (e.g., 128) in your config!
batch_size = config.get("batch_size", 8) 

# 2. Calculate the exact number of batches for the ETA calculation
# (Assuming your CSV has a header row. If not, remove the '- 1')
csv_path = config["train_csv"]
with open(csv_path, 'r') as f:
    total_chunks = sum(1 for row in f) - 1
total_batches = math.ceil(total_chunks / batch_size)


builder = DatasetBuilder(
    config, 
    audio_adapter, 
    audio_path="data"
)


train_dataset = builder.build(
    config["train_csv"], 
    cache_directory=config["training_cache"],
    batch_size=batch_size,
    infinite_generator=False 
)


 # prefetch
optimized_dataset = train_dataset.prefetch(buffer_size=tf.data.AUTOTUNE)


# 5. Iterate with tqdm to generate the progress bar
print(f"Starting cache creation with batch size {batch_size}...")
for batch in tqdm(optimized_dataset, total=total_batches, desc="Caching Spleeter Data", unit="batch"):
    # We do not need to do anything inside the loop. 
    # Just asking for the next 'batch' forces TensorFlow to compute and cache it.
    pass
        
print("Training cache successfully written to disk!")