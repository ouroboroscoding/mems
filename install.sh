#!/bin/bash

# Get the current path of the install script and make sure /mems points to it if
#	it doesn't already
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR="$( dirname "${DIR}" )"
if [ ! -d "/mems" ];  then
	ln -sf ${DIR} /mems
fi

# Install log
LOGFILE=/mems/install/install.log

# Clear the install log
echo '' > $LOGFILE

# Ask about databases
echo "Do you want to install databases locally?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) install/databases.sh $LOGFILE; break;;
        No ) break;;
    esac
done

# Run the services install
install/services.sh $LOGFILE

# Ask about dev
echo "Do you want to make development changes?"
select yn in "Yes" "No"; do
    case $yn in
        Yes ) install/dev.sh $LOGFILE; break;;
        No ) break;;
    esac
done
