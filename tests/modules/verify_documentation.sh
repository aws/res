#!/bin/bash

# require blc https://www.npmjs.com/package/broken-link-checker


cd $1/../

# Dead Links checkers. Mkdocs must be up and running
MKDOCS_URL="127.0.0.1"
MCDOCS_PORT="8000"
MKDOCS_PROTOCOL="http://"
curl -I $MKDOCS_PROTOCOL$MKDOCS_URL:$MCDOCS_PORT
if [[ $? -ne 0 ]];
  then
    echo "Documentation HTTP server is not running. To start it, run the following command"
    echo "cd $1/../ && mkdocs serve"
    exit 1
fi
blc $MKDOCS_PROTOCOL$MKDOCS_URL:$MCDOCS_PORT -ro --exclude-external

