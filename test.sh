mkdir output_directory

python -m spleeter separate -o output_directory/ -p configs/modified_config.json audiotest/testmusic.mp3

zip -r results.zip output_directory/
