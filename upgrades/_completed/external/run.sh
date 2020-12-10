!#/bin/sh

# Fix paths on existing services
cd /etc/supervisor/conf.d
sed -i 's/ rest/ nodes.rest/' *.conf

# Install new service
echo "[program:external]
command=/root/venvs/mems/bin/python -um nodes.external
directory=/mems/
autorestart=true
startretries=3
stderr_logfile=/var/log/mems/external_err.log
stdout_logfile=/var/log/mems/external_out.log
user=root" > external.conf
/usr/bin/supervisorctl reread
/usr/bin/supervisorctl update

# Install new host
echo "# External upstream
upstream external_server {
	server localhost:8100 fail_timeout=0;
}

server {

	if ($scheme != 'https') {
		return 301 https://$host$request_uri;
	}

	listen 80;
	include ssl_params;
	server_name external.meutils.com;
	access_log /var/log/mems/external.access.log;
	error_log /var/log/mems/external.error.log;

	# websocket
	location / {
		proxy_pass http://external_server;
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection \"upgrade\";

		proxy_redirect off;
		proxy_set_header Host $host;
		proxy_set_header X-Real-IP $remote_addr;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_read_timeout 600;
	}
}"
cd /etc/nginx/sites-enabled
ln -sf ../sites-available/external.conf .
sed -i 's/me\/mems\/www/me\/mems\/nodes\/www/' mems.conf
/usr/sbin/nginx -t && /usr/sbin/nginx -s reload
