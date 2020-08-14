[Unit]
Description=RQ-REST HTTP Service (rest-server).

[Service]
WorkingDirectory=${base_path}
EnvironmentFile=${base_path}/etc/rq-rest.env
ExecStart=${base_path}/bin/rq-rest rest

[Install]
WantedBy=multi-user.target