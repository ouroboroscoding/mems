add-apt-repository ppa:pypy/ppa
apt update
apt install build-essential pypy3 pypy3-dev
virtualenv -p /usr/bin/pypy3 /root/venvs/mems-pypy
/root/venvs/mems-pypy/bin/pypy3 -m pip install -r /me/mems/requirements.txt
sed -i 's/mems\/bin\/python/mems-pypy\/bin\/pypy3/' /etc/supervisor/conf.d/*.conf
supervisorctl reread
supervisorctl update
