#! /bin/bash
set -eo pipefail

CUR_DIR=$(
    cd "$(dirname "$0")"
    pwd
)

echo "CUR_DIR=$CUR_DIR"

FRONTEND_DIR="$CUR_DIR/configops-frontend"
BACKEND_DIR="$CUR_DIR/configops"

ENV="dev"
DIST=""
VERBOSE=0

print_help() {
    cat <<EOF
Usage: $0 [Options]

Options:
  -e, --env       Npm build environment
  -v, --verbose   Print debug info
  -h, --help      Print help
  -d, --dist      The dist dir

Example:
  $0 -e dev --verbose
EOF
}

while [[ "$#" -gt 0 ]]; do
    case $1 in
    -e | --env)
        ENV="$2"
        shift 2
        ;;
    -d | --dist)
        DIST="$2"
        shift 2
        ;;
    -v | --verbose)
        VERBOSE=1
        shift
        ;;
    -h | --help)
        print_help
        exit 0
        ;;
    --)
        shift
        break
        ;;
    -*)
        echo "Unknown argument: $1"
        exit 1
        ;;
    esac
done

if [ -n "$DIST" ]; then
    BACKEND_DIST="$BACKEND_DIR/static/$DIST"
else
    BACKEND_DIST="$BACKEND_DIR/static"
fi

if [ "$VERBOSE" == "1" ]; then
    echo "Frontend dir: $FRONTEND_DIR"
    echo "Backend dir: $BACKEND_DIR"
    echo "Backend dist: $BACKEND_DIST"
fi

cd $FRONTEND_DIR && pnpm run build:$ENV
mkdir -p ${BACKEND_DIST}
rm -rf ${BACKEND_DIST}/*
cp -R $FRONTEND_DIR/dist-$ENV/* ${BACKEND_DIST}
