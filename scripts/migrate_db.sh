#!/bin/bash

echo PRESS CTRL-C IF YOU HAVE NOT INITIALIZED THE MYSQL DATABASE YET
sleep 5

sqlite3mysql \
    -f CRABBER_DATABASE.db \
    -d ${MYSQL_DATABASE} \
    -u ${MYSQL_USER} \
    --mysql-password ${MYSQL_PASS} \
    -h ${MYSQL_HOST} \
    -P ${MYSQL_PORT}
