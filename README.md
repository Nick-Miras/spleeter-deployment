# Spleeter Deployment
Spleeter U-Net Audio Separator Training and Deployment on AWS.

## Structure
```
root
├── audiotest
├── configs
├── main
├── spleeter_pretrained1
├── spleeter-1.4.0
├── data
```
##### `/audiotest`
a banger song used for testing

##### `/configs`
the configuration files for spleeter

##### `/spleeter_pretrained1`
...

##### `/spleeter-1.4.0`
local copy of spleeter code

##### `/data`
directory that contains the training data and the csv files that refer to it

## Setup

### Dependencies
1. python 3.9 or 3.10
2. ffmpeg
3. zip

### Datasets
...


## Demo

**Warning!** 

Make sure to set the batch size to 1.

### Steps
To run the gradio web interface for demo purposes. First, install it using the following command:
```sh
pip install gradio
```
Once gradio is installed simply run `app.py`.

```sh
python app.py
```
The address of the web application should be `http://127.0.0.1:7860`.


## References
The full dataset is in https://huggingface.co/datasets/qrowraven/Datasetqrow.
