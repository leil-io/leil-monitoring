#!/bin/sh
docker compose -f ./compose-dev.yaml build
docker compose -f ./compose-dev.yaml up
docker compose -f ./compose-dev.yaml down
