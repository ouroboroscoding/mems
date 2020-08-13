#!/bin/bash
cd /etc/supervisor/conf.d
sed -i 's/\/me\/mems\/scripts\//\/me\/mems\//' *.conf
sed -i 's/services./rest./' *.conf
supervisorctl reread
supervisorctl update
