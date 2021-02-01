#!/bin/bash

# Turn on bold green
G='\e[1;32m'
# Reset colour
R='\e[0m'

# Change supervisor info
sed -i 's/environment=VERBOSE=0/environment=VERBOSE=1/' /etc/supervisor/supervisord.conf

# Change nginx info
sed -i 's/meutils.com/mems.local/g' /etc/nginx/sites-available/*.conf
sed -i 's/mems.com/mems.local/g' /etc/nginx/ssl_params

# Reboot nginx
/usr/sbin/nginx -s reload
