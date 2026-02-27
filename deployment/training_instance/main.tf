
resource "aws_volume_attachment" "ebs_att" {
  device_name = "/dev/sdh"
  volume_id   = "vol-06024cfa4266ffe34"
  instance_id = "${aws_instance.spleeter_training_instance.id}"
  # skip_destroy = true
}

resource "aws_instance" "spleeter_training_instance" {
  ami           = "ami-02d2c097a1e2910f5"  # Nvidia Base CUDA AMI
  instance_type = "g6.xlarge"
  key_name      = "spleeter-training"
  availability_zone = "us-east-1d"
  vpc_security_group_ids = ["sg-05d98613cfd942528", "sg-0b5f5c58a5fd8d76f"]

  root_block_device {
    volume_size = 150
    volume_type = "gp3"
    throughput = 125
    iops = 3000
  }
  tags = {
    Name = "Spleeter Training g6 Instance"
  }

  user_data = <<-EOF
      #!/bin/bash
      WORKING_DIR="/opt/dlami/nvme"

      # Install necessary packages
      apt-get install ffmpeg zip -y
      # add-apt-repository ppa:deadsnakes/ppa
      # apt update
      # apt install python3.10 python3.10-venv -y
    
      # Wait for the device to be attached
      while [ ! -e /dev/nvme1n1 ]; do sleep 1; done
      mkdir -p /mnt/thesis
      mount /dev/nvme2n1 /mnt/thesis

      # Format the drive if it hasn't been formatted yet. This is a safety check.
      # if ! file -s /dev/nvme1n1 | grep -q "filesystem"; then
      #   mkfs.ext4 /dev/nvme1n1
      # fi

      sudo -u ubuntu bash << 'EOU'
        cd /home/ubuntu/
        mkdir -p ~/miniconda3
        wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
        bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
        rm ~/miniconda3/miniconda.sh

        # Load the variables or set path again because we are in a new shell
        WORKING_DIR="/opt/dlami/nvme"
        cd "$WORKING_DIR"
        git clone https://github.com/Nick-Miras/spleeter-deployment.git thesis
        cd "$WORKING_DIR/thesis"
        
        touch installation_log.txt
        
        # --- Fix for EXTERNALLY MANAGED ENVIRONMENT ---
        # You must create the venv AND activate it within this block.
        # When the venv is active, pip checks get bypassed.
        ~/miniconda3/bin/conda config --set always_yes true

        # echo "Creating virtual environment..."
        ~/miniconda3/bin/conda env create -f environment.yaml >> installation_log.txt 2>&1

        # Initialize Conda
        ~/miniconda3/bin/conda init

        # Make the new environment activate automatically on SSH login
        echo "conda activate spleeter" >> $HOME_DIR/.bashrc

        # Finalizations
        chmod +x setup.sh train.sh
      EOU
    EOF
}

output "public_ip" {
  value = aws_instance.spleeter_training_instance.public_ip
}
