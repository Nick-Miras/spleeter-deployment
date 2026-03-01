
resource "aws_volume_attachment" "ebs_att" {
  device_name = "/dev/sdh"
  volume_id   = "vol-025382c6241f97fcb"  # TODO: Use Variables
  instance_id = "${aws_instance.spleeter_training_instance.id}"
  # skip_destroy = true
}

resource "aws_instance" "spleeter_training_instance" {
  ami           = "ami-02d2c097a1e2910f5"  # Nvidia Base CUDA AMI
  instance_type = "g4dn.xlarge"
  key_name      = "spleeter-training"
  availability_zone = "us-east-1d"
  vpc_security_group_ids = ["sg-05d98613cfd942528", "sg-0b5f5c58a5fd8d76f"]

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
    throughput = 125
    iops = 3000
  }
  tags = {
    Name = "Spleeter Training g4dn Instance"
  }

  user_data = <<-EOF
      #!/bin/bash
      WORKING_DIR="/opt/dlami/nvme"

      # Install necessary packages
      apt-get install ffmpeg zip -y

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
        
        ##########################################################
        # --- Conda Managed Environment for cudnn dependencies ---
        ##########################################################

        # Accept licenses for Anaconda packages
        ~/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
        ~/miniconda3/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r

        # echo "Creating virtual environment..."
        ~/miniconda3/bin/conda env create -f environment.yml >> installation_log.txt 2>&1

        # Initialize Conda
        ~/miniconda3/bin/conda init

        # Make the new environment activate automatically on SSH login
        echo "conda activate spleeter" >> ~/.bashrc

        # Setting Permissions
        chmod +x setup.sh train.sh test.sh

        # Copying Cache to the new environment
        cp -r /mnt/thesis/spleeter-deployment/cache/* cache/
      EOU
    EOF
}

output "public_ip" {
  value = aws_instance.spleeter_training_instance.public_ip
}
