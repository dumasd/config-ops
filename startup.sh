#!/bin/bash
DIR="$(dirname "$0")"
DIR="$(cd "$DIR" && pwd)"

if [ -z "${HOST}" ]; then
    HOST="127.0.0.1"
fi

if [ -z "${PORT}" ]; then
    PORT="5000"
fi

PID_FILE=${DIR}/config-ops.pid

# 停掉老进程
if [ -s "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if [[ -n "$PID" ]]; then
        kill -15 "$PID"
    fi
    rm -rf $PID_FILE
fi

if [ -z "${CONFIG_OPS_CONF_FILE}" ]; then
    $DIR/config-ops --host $HOST --port $PORT
else
    $DIR/config-ops --host $HOST --port $PORT --config $CONFIG_FILE
fi

echo $! >$PID_FILE
