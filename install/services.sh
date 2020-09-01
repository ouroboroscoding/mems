#!/bin/bash

# Turn on bold green
G='\e[1;32m'
# Reset colour
R='\e[0m'

# Install log
LOGFILE=$1

# Add the universe packages
echo -e "${G}Updating apt...${R}"
apt-get -qq update &>> $LOGFILE

# Redis
echo -e "${G}Installing Redis...${R}"
apt-get -qq install redis &>> $LOGFILE

# Install nginx
echo -e "${G}Installing NGINX...${R}"
apt-get -qq install nginx &>> $LOGFILE

# Install supervisor
echo -e "${G}Installing Supervisor...${R}"
apt-get -qq install supervisor &>> $LOGFILE

# Install python virtalenv
echo -e "${G}Installing PIP and Virtualenv for Python3...${R}"
apt-get -qq install python3-pip &>> $LOGFILE
pip3 -q install virtualenv &>> $LOGFILE
mkdir -p /root/venvs/mems
virtualenv -p /usr/bin/python3 /root/venvs/mems &>> $LOGFILE
/root/venvs/mems/bin/pip install -r /mems/requirements.txt &>> $LOGFILE

# Make folders and copy etc files
echo -e "${G}Making folders, copying server config files, and creating aliases...${R}"
# log directory
mkdir -p /var/log/mems  &>> $LOGFILE
# copy etc files
cp -R /mems/install/services/* / &>> $LOGFILE
# nginx fix
cd /etc/nginx/sites-enabled
ln -sf ../sites-available/www.conf .
# Aliases
echo "alias lf='ls -aCF'" >> ~/.bashrc
echo "alias src_mems='source /root/venvs/mems/bin/activate; cd /mems'" >> ~/.bashrc

# Restart services
echo -e "${G}Restarting services...${R}"
# Remove the default redis server
systemctl disable redis-server &>> $LOGFILE
service redis-server stop &>> $LOGFILE
rm -f /etc/init.d/redis-server &>> $LOGFILE
# Install the primary redis server
update-rc.d redis-primary defaults &>> $LOGFILE
service redis-primary start &>> $LOGFILE
# Restart nginx
service nginx restart &>> $LOGFILE
