#!/bin/bash
docker-compose run thresher_api sh /home/thresher/docker/thresher_api/init_django.sh
docker-compose run thresher_api sh /home/thresher/docker/thresher_api/init_users.sh