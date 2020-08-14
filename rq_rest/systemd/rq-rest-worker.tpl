[Unit]
Description=RQ-REST worker for queue '%I'.
After=network-online.target nginx.service
Wants=network-online.target

[Service]
WorkingDirectory=${base_path}
EnvironmentFile=${base_path}/etc/%I.env
ExecStart=${base_path}/bin/rq-rest worker -s %I

[Install]
WantedBy=multi-user.target