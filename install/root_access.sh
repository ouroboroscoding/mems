#!/bin/bash

echo -e "\e[1;32mInstalling root access...\e[0m"

# Add autologin as root
mkdir -pv /etc/systemd/system/getty@tty1.service.d/
echo "
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin root --noclear %I 38400 linux" >> /etc/systemd/system/getty@tty1.service.d/autologin.conf

# Allow root ssh access
passwd root
passwd -u root
sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
service ssh restart
