Zabbix-Alerta Gateway
=====================

Consolidate Zabbix alerts from across multiple sites into a single "at-a-glance" console by using a custom Zabbix [alertscript](https://www.zabbix.com/documentation/2.2/manual/config/notifications/media/script).

Transform this ...

![zabbix](/docs/images/zabbix-alerta-before.png?raw=true)

Into this ...

![alerta](/docs/images/zabbix-alerta-after.png?raw=true)

Installation
------------

Copy the `zabbix_alerta.py` script into the `AlertScriptsPath` directory which is by default `/usr/lib/zabbix/alertscripts` and make it executable:

    $ wget https://raw.github.com/alerta/zabbix-alerta/master/zabbix_alerta.py
    $ cp zabbix_alerta.py /usr/lib/zabbix/alertscripts
    $ chmod 755 /usr/lib/zabbix/alertscripts/zabbix_alerta.py

Configuration
-------------

To forward zabbix events to Alerta a new media script needs to be created and associated with a user. Follow the steps below as a Zabbix Admin user...

1/ Create a new media type [Admininstration > Media Types > Create Media Type]

```
Name: Alerta API
Type: Script
Script name: zabbix_alerta.py
```

2/ Modify the Media for the Admin user [Administration > Users]

```
Type: alerta
Send to: http://x.x.x.x:8080         <--- API hostname/IP and port of alerta server
When active: 1-7,00:00-24:00
Use if severity: (all)
Status: Enabled
```
**Note:** If API authentication is enabled then an API key will need to be specified in the `Send to` configuration. The API key is added after the API endpoint separated only by a semicolon. eg. `http://x.x.x.x;YOUR_API_KEY_HERE`

3/ Configure Action [Configuration > Actions > Create Action > Action]

```
Name: Forward to Alerta
Default Subject: {TRIGGER.STATUS}: {TRIGGER.NAME}
```

```
Default Message:

resource={HOST.NAME1}
event={ITEM.KEY1}
group=Zabbix
value={ITEM.VALUE1}
status={TRIGGER.STATUS}
severity={TRIGGER.SEVERITY}
ack={EVENT.ACK.STATUS}
environment=Production
service={TRIGGER.HOSTGROUP.NAME}
text={TRIGGER.NAME}
type=zabbixAlert
tags=ipaddr={HOST.IP1},id={TRIGGER.ID},event_id={EVENT.ID}
thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}
```

For a full list of trigger macros see https://www.zabbix.com/documentation/2.2/manual/appendix/macros/supported_by_location

To send OK events ...

````
Recovery message: [check]
Enabled [check]
````

At the Conditions tab, to only forward PROBLEM and OK events ...

```
(A)	Maintenance status not in "maintenance"
(B)	Trigger value = "PROBLEM"
```

To forward PROBLEM, ACKNOWLEDGED, OK events ...

```
(A)	Maintenance status not in "maintenance"
```

Finally, add an operation:

```
Send to Users: Admin
Send only to: Alerta API
```

More Information
----------------

See the [PagerDuty guide to configuring Zabbix integrations][1] for an alertnative explanation with screenshots.

[1]: <http://www.pagerduty.com/docs/guides/zabbix-integration-guide/> "PagerDuty Zabbix Integration Guide"

License
-------

Copyright (c) 2014 Nick Satterly. Available under the MIT License.
