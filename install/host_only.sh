#!/bin/bash

echo -e "\e[1;32mInstalling host only network...\e[0m"

echo "
network:
    ethernets:
        enp0s3:
            addresses: []
            dhcp4: true
        enp0s8:
            addresses: [192.168.56.30/24]
            dhcp4: false
    version: 2" > /etc/netplan/50-cloud-init.yaml

netplan apply
