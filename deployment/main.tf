resource "aws_security_group" "allow_ssh" {
  name        = "allow_ssh"
  description = "Allow devices to SSH into the machine."

  tags = {
    Name = "VPC security group for SSH access."
  }
}

resource "aws_vpc_security_group_ingress_rule" "allow_all_traffic_ssh" {
  security_group_id = aws_security_group.allow_ssh.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = "22"
  to_port           = "22"
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv4" {
  security_group_id = aws_security_group.allow_ssh.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1" # all ports
}

resource "aws_vpc_security_group_egress_rule" "allow_all_traffic_ipv6" {
  security_group_id = aws_security_group.allow_ssh.id
  cidr_ipv6         = "::/0"
  ip_protocol       = "-1" # all ports
}

resource "aws_instance" "llm_training_instance" {
  ami           = "ami-07b531d2a90722369"
  instance_type = var.instance_type
  key_name      = "spleeter-training"
  vpc_security_group_ids = [aws_security_group.allow_ssh.id]

  root_block_device {
    volume_size = 256
    volume_type = "gp3"
  }
  tags = {
    Name = "Spleeter Training G6 Instance"
  }

  user_data = <<-EOF
      #!/bin/bash
      WORKING_DIR="/opt/dlami/nvme"

      # Install necessary packages
      apt install python3-pip -y
    
      # Wait for the device to be attached
      while [ ! -e /dev/nvme1n1 ]; do sleep 1; done

      cd $WORKING_DIR
      git clone https://github.com/Nick-Miras/spleeter-deployment.git thesis
      chown -R ubuntu:ubuntu thesis
      chmod -R 744 thesis
      cd thesis
      chmod -R 755 src

      sudo -u ubuntu bash << 'EOU'
        # Load the variables or set path again because we are in a new shell
        WORKING_DIR="/opt/dlami/nvme"
        cd "$WORKING_DIR/thesis"
        
        touch installation_log.txt
        
        # --- Fix for EXTERNALLY MANAGED ENVIRONMENT ---
        # You must create the venv AND activate it within this block.
        # When the venv is active, pip checks get bypassed.
        
        echo "Creating virtual environment..."
        python3 -m venv .venv
        
        echo "Activating virtual environment..."
        source .venv/bin/activate
        
        echo "Installing dependencies..."
        # Now that venv is active, pip will install into .venv/lib 
        # and not conflict with the system python.
        pip install -r requirements.txt > installation_log.txt 2>&1
      EOU
    EOF
}

output "public_ip" {
  value = aws_instance.llm_training_instance.public_ip
}
