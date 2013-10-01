Zabbix-Alerta Gateway
=====================

Consolidate Zabbix alerts from across multiple sites into a single "at-a-glance" console.

Transform this ...

![zabbix](/docs/images/zabbix.png?raw=true)

Into this ...

![alerta](/docs/images/alerta.png?raw=true)

Installation
------------

    $ cp zabbix_alerta.py /usr/share/zabbix/alertscripts
    $ cd /usr/share/zabbix/alertscripts
    $ chmod +x zabbix_alerta.py
    $ chown zabbix:users zabbix_alerta.py

Configuration
-------------

1. Configure Action

Name: `Forward to Alerta`
Default `Subject: {TRIGGER.STATUS}: {TRIGGER.NAME}`

Default Message:
```
resource={HOST.NAME1}
event={ITEM.KEY1}
group=Zabbix
value={ITEM.VALUE1}
status={TRIGGER.STATUS}
severity={TRIGGER.SEVERITY}
ack={EVENT.ACK.STATUS}
environment=INFRA
service={TRIGGER.HOSTGROUP.NAME}
text={TRIGGER.NAME}
type=zabbixAlert
tags=ipaddr:{HOST.IP1}
thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}
moreInfo={TRIGGER.DESCRIPTION}
```


License
-------

Copyright (c) 2013 Nick Satterly. Available under the MIT License.

