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
apt-get -qq update &>> $LOGFILE

# MySQL
echo -e "${G}Installing MySQL...${R}"
debconf-set-selections <<< 'mysql-server mysql-server/root_password password mems'
debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password mems'
apt-get -qq install mysql-server &>> $LOGFILE
sed -i 's/bind-address\t\t= 127.0.0.1/#bind-address = 127.0.0.1/' /etc/mysql/mysql.conf.d/mysqld.cnf
echo "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' IDENTIFIED BY 'mems'" | mysql -uroot -pmems &>> $LOGFILE

# Make folders and copy etc files
echo -e "${G}Copying server config files...${R}"
# copy etc files
cp -R /mems/install/databases/* / &>> $LOGFILE

# Restart services
echo -e "${G}Restarting services...${R}"
# Restart mysql
service mysql restart &>> $LOGFILE
