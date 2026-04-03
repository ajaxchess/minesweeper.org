# Configure the GCP Provider
provider "google" {
  project = "YOUR_PROJECT_ID" # Replace with your GCP Project ID
  region  = "us-central1"
}

# Reserve a Static External IP address
resource "google_compute_address" "static_ip" {
  name   = "pgl-minesweeper-static-ip"
  region = "us-central1"
}

# Firewall Rule: Allow HTTP and HTTPS
resource "google_compute_firewall" "web_firewall" {
  name    = "allow-web-traffic"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["web-server"]
}

# Firewall Rule: Allow SSH
resource "google_compute_firewall" "ssh_firewall" {
  name    = "allow-ssh-traffic"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["web-server"]
}

# Compute Instance
resource "google_compute_instance" "web_server" {
  name         = "pgl-minesweeper-web"
  machine_type = "e2-micro"
  zone         = "us-central1-a"
  tags         = ["web-server"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 30 # Free Tier allows up to 30GB of Standard Persistent Disk
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.static_ip.address
    }
  }

  # Startup Script: Handles Swap, Software Install, and DB Setup
  metadata_startup_script = <<-EOT
    #!/bin/bash
    set -e

    # 1. Setup 2GB Swap File (Crucial for 1GB RAM instances)
    if [ ! -f /swapfile ]; then
      fallocate -l 2G /swapfile
      chmod 600 /swapfile
      mkswap /swapfile
      swapon /swapfile
      echo '/swapfile none swap sw 0 0' >> /etc/fstab
    fi

    # 2. Update and Install Stack
    apt-get update
    export DEBIAN_FRONTEND=noninteractive
    apt-get install -y apache2 \
                       mysql-server \
                       python3-pip \
                       python3-venv \
                       git \
                       certbot \
                       python3-certbot-apache \
                       libapache2-mod-proxy-uwsgi \
                       pkg-config \
                       libmysqlclient-dev

    # 3. Configure Apache Modules
    a2enmod proxy proxy_http ssl rewrite headers

    # 4. Start and Enable Services
    systemctl start mysql
    systemctl enable mysql
    systemctl start apache2
    systemctl enable apache2

    # 5. Initialize MySQL (Change 'password123' to a secure password)
    mysql -e "CREATE DATABASE IF NOT EXISTS pgl_db;"
    mysql -e "CREATE USER IF NOT EXISTS 'pgl_admin'@'localhost' IDENTIFIED BY 'password123';"
    mysql -e "GRANT ALL PRIVILEGES ON pgl_db.* TO 'pgl_admin'@'localhost';"
    mysql -e "FLUSH PRIVILEGES;"

    # 6. Set up basic directory for the app
    mkdir -p /var/www/pgl-minesweeper
    chown -R ubuntu:ubuntu /var/www/pgl-minesweeper
  EOT

  metadata = {
    enable-oslogin = "TRUE"
  }
}

# Output the Static IP to use for DNS setup
output "server_public_ip" {
  value       = google_compute_address.static_ip.address
  description = "The static IP address to point pgl.minesweeper.org to."
}
