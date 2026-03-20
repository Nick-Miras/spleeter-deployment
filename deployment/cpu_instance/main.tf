resource "aws_volume_attachment" "ebs_att" {
  device_name = "/dev/sdh"
  volume_id   = "vol-025382c6241f97fcb"
  instance_id = "${aws_instance.spleeter_caching_instance.id}"
}

resource "aws_instance" "spleeter_caching_instance" {
  ami           = "ami-07b531d2a90722369"
  instance_type = "c6a.2xlarge"
  key_name      = "spleeter-training"
  availability_zone = "us-east-1d"
  vpc_security_group_ids = ["sg-05d98613cfd942528"]

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
    throughput = 125
    iops = 3000
  }
  tags = {
    Name = "Spleeter Data-Preloading c6a Instance"
  }

  user_data = <<-EOF
      #!/bin/bash
      WORKING_DIR="/mnt/thesis"
      DEVICE="/dev/nvme1n1"

      # Install necessary packages

      apt-get install ffmpeg zip -y
      add-apt-repository ppa:deadsnakes/ppa
      apt update
      apt install python3.10 python3.10-venv -y
    
      # Wait for the device to be attached TODO: Attach Volume in Terraform.
      while [ ! -e $DEVICE ]; do sleep 1; done

      # Format the drive if it hasn't been formatted yet. This is a safety check.
      if ! file -s $DEVICE | grep -q "filesystem"; then
        mkfs.ext4 $DEVICE
      fi

      # Mount Drive
      mkdir -p $WORKING_DIR
      mount $DEVICE $WORKING_DIR
      chown ubuntu:ubuntu $WORKING_DIR
      

      sudo -u ubuntu bash << 'EOU'
        # Load the variables or set path again because we are in a new shell
        WORKING_DIR="/mnt/thesis/spleeter-deployment"
        cd "$WORKING_DIR"
        git clone https://github.com/Nick-Miras/spleeter-deployment.git
        
        touch installation_log.txt
        
        # --- Fix for EXTERNALLY MANAGED ENVIRONMENT ---
        # You must create the venv AND activate it within this block.
        # When the venv is active, pip checks get bypassed.
        
        echo "Creating virtual environment..."
        python3.10 -m venv .venv
        
        echo "Activating virtual environment..."
        source .venv/bin/activate
        
        echo "Installing dependencies..."
        # Now that venv is active, pip will install into .venv/lib 
        # and not conflict with the system python.
        pip install -r requirements.txt > installation_log.txt 2>&1

        # Finalizations
        chmod +x setup.sh train.sh
      EOU
    EOF
}

output "public_ip" {
  value = aws_instance.spleeter_caching_instance.public_ip
}
