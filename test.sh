mkdir output_directory

python -m spleeter separate -o output/ -p configs/config.json audiotest/testmusic.mp3

zip -r results.zip output/
