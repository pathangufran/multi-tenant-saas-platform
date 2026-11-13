#!/bin/sh

set -eu

envsubst < /etc/pgbouncer/pgbouncer.ini.template \
    > /etc/pgbouncer/pgbouncer.ini

exec pgbouncer \
    /etc/pgbouncer/pgbouncer.ini