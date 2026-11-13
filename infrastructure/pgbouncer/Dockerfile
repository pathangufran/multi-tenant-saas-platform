FROM alpine:3.22

RUN apk add --no-cache \
    pgbouncer \
    gettext \
    su-exec

COPY pgbouncer.ini.template /etc/pgbouncer/pgbouncer.ini.template
COPY userlist.txt /etc/pgbouncer/userlist.txt

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

EXPOSE 6432

ENTRYPOINT ["/entrypoint.sh"]