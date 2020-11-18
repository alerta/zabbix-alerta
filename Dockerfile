FROM zabbix/zabbix-server-mysql:alpine-latest

USER root

RUN apk update && \
    apk add py-pip git

RUN set -x && \
  pip install pip --upgrade && \
  pip install --no-cache-dir git+https://github.com/alerta/zabbix-alerta
