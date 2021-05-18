#!/bin/bash

MYDIR=`dirname $0`

HOSTNAME_COMP=`hostname | cut -d '-' -f 1`
MYORIGIN=`hostname -f`
MYORIGIN_STAGING=$HOSTNAME_COMP.staging.`hostname -d`

cd $MYDIR/../
bokeh serve --port $1 --disable-index --allow-websocket-origin=$MYORIGIN --allow-websocket-origin=$MYORIGIN_STAGING coviz

