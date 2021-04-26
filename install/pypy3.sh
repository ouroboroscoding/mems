add-apt-repository ppa:pypy/ppa
apt update
apt install pypy3 pypy3-dev
virtualenv -p /usr/bin/pypy3 /root/venvs/mems-pypy
/root/venvs/mems-pypy/bin/pip install -r /mems/requirements.txt
sed -i 's/mems\/bin\/python/mems-pypy\/bin\/pypy3/' /etc/supervisor/conf.d/*.conf
supervisorctl restart all
