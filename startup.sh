#!/bin/bash
DIR="$(dirname "$0")"
DIR="$(cd "$DIR" && pwd)"

if [ -z "${CONFIGOPS_HOST}" ]; then
    CONFIGOPS_HOST="127.0.0.1"
fi

if [ -z "${CONFIGOPS_PORT}" ]; then
    CONFIGOPS_PORT="5000"
fi

RUN_ARGS="--host ${CONFIGOPS_HOST} --port ${CONFIGOPS_PORT}"

if [ -n "${CONFIGOPS_CONFIG_FILE}" ]; then
    RUN_ARGS="${RUN_ARGS} --config ${CONFIGOPS_CONFIG_FILE}"

PID_FILE=${DIR}/config-ops.pid
# 停掉老进程
if [ -s "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if [[ -n "$PID" ]]; then
        kill -15 "$PID"
    fi
    rm -rf $PID_FILE
fi

nohup $DIR/config-ops $RUN_ARGS >$DIR/config-ops.log 2>&1 &

echo $! >$PID_FILE
