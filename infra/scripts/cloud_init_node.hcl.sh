#!/usr/bin/env bash
sleep 3m
echo "Cloud Init Started"


# INSTALL SYSTEM PACKAGES
sudo apt-get install -y unzip tree redis-tools jq curl tmux git resolvconf apt-transport-https ca-certificates curl gnupg lsb-release

# ****************************************************************
# ADD APT REPOSITORY SOURCES
# ****************************************************************

echo \
  "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add -

sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main"
sudo add-apt-repository -y ppa:openjdk-r/ppa

sudo apt-get update

# INSTALL DOCKER
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose

# INSTALL JAVA
sudo apt-get update
sudo apt-get install -y openjdk-8-jdk

# INSTALL HASHICORP-CONSUL, NOMAD

sudo apt-get install -y consul nomad

# INSTALL JQ
curl --silent -Lo /bin/jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64
sudo chmod +x /bin/jq

echo "Configuring system time"
timedatectl set-timezone UTC

# ****************************************************************
# CONFIG FILES
# ****************************************************************

sudo mkdir /etc/consul.d
sudo mkdir /etc/nomad.d
sudo mkdir /etc/traefik

# SETUP CONFIGURATION FILES
sudo cp /home/ubuntu/cloudinit/consul.agent.json /etc/consul.d/consul.json
sudo cp /home/ubuntu/cloudinit/consul.service /etc/systemd/system/consul.service
sudo cp /home/ubuntu/cloudinit/nomad.hcl /etc/nomad.d/nomad.hcl
sudo cp /home/ubuntu/cloudinit/netplan_60-static.yaml /etc/netplan/60-static.yaml
sudo cp /home/ubuntu/cloudinit/daemon.json /etc/docker/daemon.json

sudo chown -R nomad:nomad /etc/nomad.d
sudo chmod -R 640 /etc/nomad.d/*
sudo chmod 600 /etc/traefik/acme.json

mkdir /home/nomad
mkdir /home/nomad/job-volumes

# ****************************************************************
# CONSUL
# ****************************************************************

sudo systemctl enable consul
sudo systemctl start consul

sleep 60

sudo systemctl enable nomad
sudo systemctl start nomad

sleep 60

echo "Cloud Init Completed"
