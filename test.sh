#!/bin/bash
cd $(cd $(dirname $0) && pwd)
find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf >/dev/null 2>&1

test -d build && rm -r build
test -d dist && rm -r dist
test -d *.egg-info && rm -r *.egg-info

docker build -f Dockerfile_dev -t fastkit:dev .
docker run \
    --rm -ti \
    --net host \
    -e flyer_port=8889 \
    -e flyer_access_log=1 \
    -v $(pwd):/fastkit \
    fastkit:dev \
    bash

test -d build && rm -r build
test -d dist && rm -r dist
test -d *.egg-info && rm -r *.egg-info
