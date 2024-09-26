bind = "0.0.0.0:9000"
workers = 2
threads = 4
max_requests = 1000
worker_class = "gthread"
accesslog = "media/gunicorn_access.log"
errorlog = "media/gunicorn_error.log"
