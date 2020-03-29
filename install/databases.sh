#!/bin/bash

# Turn on bold green
G='\e[1;32m'
# Reset colour
R='\e[0m'

# Set the logfile
LOGFILE=$1

# Add the universe packages
echo -e "${G}Updating apt...${R}"
apt-get -qq install software-properties-common &>> $LOGFILE
apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8 &>> $LOGFILE
add-apt-repository 'deb [arch=amd64,arm64,ppc64el] http://mirror.lstn.net/mariadb/repo/10.4/ubuntu bionic main' &>> $LOGFILE
apt-get -qq update &>> $LOGFILE

# Redis
echo -e "${G}Installing Redis...${R}"
apt-get -qq install redis &>> $LOGFILE

# MariaDB
echo -e "${G}Installing MariaDB...${R}"
debconf-set-selections <<< 'mariadb-server mysql-server/root_password password mems'
debconf-set-selections <<< 'mariadb-server mysql-server/root_password_again password mems'
apt-get -qq install mariadb-server &>> $LOGFILE
sed -i 's/bind-address\t\t= 127.0.0.1/#bind-address = 127.0.0.1/' /etc/mysql/my.cnf

# Make folders and copy etc files
echo -e "${G}Making copying server config files...${R}"
# copy etc files
cp -R /mems/install/databases/* / &>> $LOGFILE

# Restart services
echo -e "${G}Restarting services...${R}"
# Remove the default redis server
systemctl disable redis-server &>> $LOGFILE
service redis-server stop &>> $LOGFILE
rm -f /etc/init.d/redis-server &>> $LOGFILE
# Install the primary redis server
update-rc.d redis-primary defaults &>> $LOGFILE
service redis-primary start &>> $LOGFILE
# Restart mariadb
service mysql restart &>> $LOGFILE
