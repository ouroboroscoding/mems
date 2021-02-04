apt-get -qq install software-properties-common
add-apt-repository ppa:certbot/certbot
apt-get -qq update
apt-get -qq install python-certbot-nginx
apt-get -qq install python-pip
mkdir -p /root/venvs/certbot
virtualenv -p /usr/bin/python3 /root/venvs/certbot

# AWS dns authenticator
/root/venvs/certbot/bin/pip install certbot_dns_route53

# Custom cpanel dns authenticator
/root/venvs/certbot/bin/pip install certbot-cpanel

# MeMS and most UIs (meutils.com, *.meutils.com)
/root/venvs/certbot/bin/certbot certonly --dns-route53 --dns-route53-propagation-seconds 30 -d meutils.com -d *.meutils.com --server https://acme-v02.api.letsencrypt.org/directory

# Patient Portal (my.maleexel.com)
/root/venvs/certbot/bin/certbot certonly --authenticator certbot-cpanel:dns-cpanel --certbot-cpanel:dns-cpanel-propagation-seconds 30 -d my.maleexcel.com --server https://acme-v02.api.letsencrypt.org/directory

# Link Shortener (link.maleexcel.com)
/root/venvs/certbot/bin/certbot certonly --authenticator certbot-cpanel:dns-cpanel --certbot-cpanel:dns-cpanel-propagation-seconds 30 -d link.maleexcel.com --server https://acme-v02.api.letsencrypt.org/directory
