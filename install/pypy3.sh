add-apt-repository ppa:pypy/ppa
apt update
apt install build-essential pypy3 pypy3-dev
virtualenv -p /usr/bin/pypy3 /root/venv/mems-pypy
/root/venv/mems-pypy/bin/pip install -r /me/mems/requirements.txt
sed -i 's/mems\/bin\/python/mems-pypy\/bin\/pypy3/' /etc/supervisor/conf.d/*.conf
supervisorctl reread
supervisorctl update
