FROM zabbix/zabbix-server-mysql:alpine-latest

RUN apk update && \
    apk add py-pip git

RUN set -x && \
  pip install pip --upgrade && \
  pip install git+https://github.com/alerta/zabbix-alerta

RUN zac --server http://zabbix-web --trapper zabbix-server -w http://alerta:8080/api
