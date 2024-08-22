#!/bin/bash
DIR="$(dirname "$0")"
DIR="$(cd "$DIR" && pwd)"

if [ -z "${HOST}" ]; then
    HOST="127.0.0.1"
fi

if [ -z "${PORT}" ]; then
    PORT="5000"
fi

if [ -z "${CONFIG}" ]; then
    CONFIG="config.yaml"
fi

$DIR/config-ops --host $HOST --port $PORT --config $CONFIG
