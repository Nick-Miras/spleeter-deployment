import tensorflow as tf
from spleeter.utils.configuration import load_configuration
from spleeter.dataset import DatasetBuilder
from spleeter.audio.adapter import AudioAdapter


config = load_configuration("configs/modified_config.json")
audio_adapter = AudioAdapter.default()


builder = DatasetBuilder(
    config, 
    audio_adapter, 
    audio_path="data"
)


train_dataset = builder.build(
    config["train_csv"], 
    cache_directory=config["training_cache"],
    batch_size=128
)


 # prefetch
optimized_dataset = train_dataset.prefetch(buffer_size=tf.data.AUTOTUNE)
        
        
print("Caching training data... This will maximize your CPU usage.")
for i, batch in enumerate(optimized_dataset):
    if i % 50 == 0:
        print(f"Processed {i} chunks...")
        
print("Training cache successfully written to disk!")
