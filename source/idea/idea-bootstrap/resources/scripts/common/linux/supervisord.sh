#!/bin/bash
#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
#  with the License. A copy of the License is located at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
#  OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
#  and limitations under the License.

# Begin: supervisord config
echo -e "; idea app supervisord config file

[unix_http_server]
file=/run/supervisor.sock
chmod=0700
chown=root:root

[supervisord]
logfile=/var/log/supervisord.log
logfile_maxbytes=50MB
logfile_backups=10
loglevel=info
pidfile=/run/supervisord.pid
nodaemon=false
minfds=1024
minprocs=200
user=root

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///run/supervisor.sock

[include]
files = supervisord.d/*.ini
" > /etc/supervisord.conf

mkdir -p /etc/supervisord.d

echo "[Unit]
Description=supervisord - Supervisor process control system for UNIX
Documentation=http://supervisord.org
After=network.target

[Service]
Type=forking
EnvironmentFile=/etc/environment
ExecStart=/opt/idea/python/latest/bin/supervisord -c /etc/supervisord.conf
ExecReload=/opt/idea/python/latest/bin/supervisorctl -c /etc/supervisord.conf reload
ExecStop=/opt/idea/python/latest/bin/supervisorctl -c /etc/supervisord.conf shutdown
User=root

[Install]
WantedBy=multi-user.target
" > /etc/systemd/system/supervisord.service

systemctl enable supervisord
systemctl restart supervisord

# End: supervisord config
