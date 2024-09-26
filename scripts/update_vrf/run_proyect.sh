#!/usr/bin/bash

# HUBO UN PROBLEMA CON EL DOCKER AL INGRESAR AL SERVIDOR CRT

docker container run  -itd --name apis_hitss -v $PWD:/work -w /work --env-file .env -p 9000:80 python:3.10.14-alpine3.19 

docker container exec -it apis_hitss pip install -r requeriments.txt

docker container exec -it apis_hitss apk add openssh

docker container exec -it apis_hitss adduser -u 1000 -D -s /bin/sh hitss

docker container exec --user $(id -u):$(id -g) -it apis_hitss sh


##  RUN GUNICORN
gunicorn webservice.wsgi:application -c gunicorn_config.py 