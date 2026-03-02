#!/bin/sh
# Start nginx as background daemon, then exec gunicorn as PID 1.
# docker stop sends SIGTERM → gunicorn (PID 1) shuts down gracefully.

nginx
exec gunicorn -c gunicorn.conf.py 'scoda_engine.serve_web:create_app()'
