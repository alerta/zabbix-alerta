Zabbix-Alerta Gateway
=====================

Consolidate Zabbix alerts from across multiple sites into a single
"at-a-glance" console by using a custom Zabbix [alertscript](https://www.zabbix.com/documentation/current/manual/config/notifications/media/script).

Transform this ...

![zabbix](/docs/images/zabbix-alerta-before.png?raw=true)

Into this ...

![alerta](/docs/images/zabbix-alerta-after.png?raw=true)

For help, join [![Slack chat](https://img.shields.io/badge/chat-on%20slack-blue?logo=slack)](https://slack.alerta.dev)

Installation
------------

Clone the GitHub repo and run:

    $ python setup.py install

Or, to install remotely from GitHub run:

    $ pip install git+https://github.com/alerta/zabbix-alerta

Then symlink the `zabbix-alerta` script to the `AlertScriptsPath` directory
which can be found in the `/etc/zabbix/zabbix_server.conf` configuration file:

    $ grep -e '^AlertScriptsPath' /etc/zabbix/zabbix_server.conf
    AlertScriptsPath=/path/to/zabbix/alertscripts
    $ ln -s `which zabbix-alerta` /path/to/zabbix/alertscripts

Configuration
-------------

To forward Zabbix events to Alerta a new media script needs to be created
and associated with a user. Follow the steps below as a Zabbix Admin user...

1/ Create a new media type [Admininstration > Media Types > Create Media Type]

```
Name: Alerta
Type: Script
Script name: zabbix-alerta
Script parameters:
    1st: {ALERT.SENDTO}
    2nd: {ALERT.SUBJECT}
    3rd: {ALERT.MESSAGE}
Enabled: [x]
```

2/ Modify the Media for the Admin user [Administration > Users]

```
Type: Alerta
Send to: http://x.x.x.x:8080   => API hostname/IP and port of alerta server
When active: 1-7,00:00-24:00
Use if severity: (all)
Status: Enabled
```

**Note:** If the [Docker container for Alerta](https://hub.docker.com/r/alerta/alerta-web/)
is used then the "Send to" URL will use a host and port specific to
your environment and the URL path will need to include `/api` eg. `http://x.x.x.x:8080/api`.

**Note:** If API authentication is enabled then an API key will need to be
specified in the `Send to` configuration. The API key is added after the API
endpoint separated only by a semicolon. eg. `http://x.x.x.x;YOUR_API_KEY_HERE`

3/ Configure Action [Configuration > Actions > Create Action > Action]

```
Name: Forward to Alerta
```
```
Default subject:
{TRIGGER.STATUS}: {TRIGGER.NAME}
```
```
Default message:
resource={HOST.NAME1}
event={ITEM.KEY1}
environment=Production
severity={TRIGGER.SEVERITY}
status={TRIGGER.STATUS}
ack={EVENT.ACK.STATUS}
service={TRIGGER.HOSTGROUP.NAME}
group=Zabbix
value={ITEM.VALUE1}
text={TRIGGER.STATUS}: {TRIGGER.NAME}
tags={EVENT.TAGS}
attributes.ip={HOST.IP1}
attributes.thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}
type=zabbixAlert
dateTime={EVENT.DATE}T{EVENT.TIME}Z

```

RECOVERY
```
Default subject:
{TRIGGER.STATUS}: {TRIGGER.NAME}
```
```
Default message:
resource={HOST.NAME1}
event={ITEM.KEY1}
environment=Production
severity={TRIGGER.SEVERITY}
status={TRIGGER.STATUS}
ack={EVENT.ACK.STATUS}
service={TRIGGER.HOSTGROUP.NAME}
group=Zabbix
value={ITEM.VALUE1}
text={TRIGGER.STATUS}: {ITEM.NAME1}
tags={EVENT.RECOVERY.TAGS}
attributes.ip={HOST.IP1}
attributes.thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}
attributes.moreInfo=<a href="http://x.x.x.x/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.RECOVERY.ID}">Zabbix console</a>
type=zabbixAlert
dateTime={EVENT.RECOVERY.DATE}T{EVENT.RECOVERY.TIME}Z
```

https://www.zabbix.com/documentation/current/manual/appendix/macros/supported_by_location

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

Advanced Configuration
----------------------

Additional features are available that enhance the integration
between Zabbix and Alerta if configuration profiles are used instead
of the basic `URL;Key` format described above.

**Configuration Profiles**

Additional configuration options are available if you use a profile for
the `sendto` value.

  * endpoint
  * API key
  * disable ssl verify
  * debug

Define `ALERTA_CONF_FILE` env var in the `/etc/default/zabbix-server` file
so that `zabbix-alerta` can find configuration settings during startup:

    $ sudo vi /etc/default/zabbix-server
    START=yes
    ALERTA_CONF_FILE=/etc/alerta.conf    => default: /var/lib/zabbix/.alerta.conf

Create the configuration file referred to by the `ALERTA_CONF_FILE` file
above that contains one or more configuration profiles:

    $ sudo vi /etc/alerta.conf
    [default]
    profile = production

    [profile production]
    endpoint = https://api.alerta.io
    key = XCYxMmPYUKHRmm-V-rYHGpzA2vveC8yT7zuvid7B
    sslverify = on
    debug = off

    [profile development]
    endpoint = http://localhost:8080
    key = demo-key
    sslverify = off
    debug = on

Use a profile name instead of the API URL in the "Send to" input box:

2/ Modify the Media for the Admin user [Administration > Users]

```
Type: Alerta
Send to: production    <= profile not URL
When active: 1-7,00:00-24:00
Use if severity: (all)
Status: Enabled
```

**Setting Alert Environment**

Using a custom user macro called `{$ENVIRONMENT}` it is possible to
set the environment of alerts received by Alerta in Zabbix. By default
the environment will be `Production` but this can be overidden at the host,
template group or global level using the `{$ENVIRONMENT}` macro.

**Use Zabbix severity levels and colours in Alerta**

Alerta can display alerts using the Zabbix standard severity names and
colours and sorted correctly by priority.

Zabbix uses the following severity hierarchy:

    Numerical trigger severity. Possible values:
    0 - Not classified,
    1 - Information,
    2 - Warning,
    3 - Average,
    4 - High,
    5 - Disaster.
    Supported starting from Zabbix 1.6.2.

In zabbix config append `!!` to the `severity` line to tell `zabbix-alerta`
to use the supplied Trigger severity and not to map the value to the
Alerta severity:

```
Default message:
resource={HOST.NAME1}
event={ITEM.KEY1}
environment=Production
severity={TRIGGER.SEVERITY}!!
status={TRIGGER.STATUS}
ack={EVENT.ACK.STATUS}
service={TRIGGER.HOSTGROUP.NAME}
...
```

Add the following to the Alerta server configuration file `alertad.conf`:

```python
SEVERITY_MAP = {
    'Disaster'      : 0,
    'High'          : 1,
    'Average'       : 2,
    'Warning'       : 3,
    'Information'   : 4,
    'OK'            : 5,
    'Not classified': 6,
    'unknown'       : 9
}
DEFAULT_NORMAL_SEVERITY = 'OK'
DEFAULT_PREVIOUS_SEVERITY = 'Not classified'

COLOR_MAP = {
    'severity': {
        'Disaster'      : '#E45959',
        'High'          : '#E97659',
        'Average'       : '#FFA059',
        'Warning'       : '#FFC859',
        'Information'   : '#7499FF',
        'Not classified': '#97AAB3',
        'OK'            : '#59DB8F',
        'unknown'       : '#BA2222'
    }
}
```

![zabbix-severity-colors](/docs/images/zabbix-severity-colors.png?raw=true)

**Zabbix Console Integration**

To add a web link in Alerta that links to the specific event in Zabbix
that triggered the alert add:

ACTION:

attributes.moreInfo=\<a href="http://x.x.x.x/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.ID}">Zabbix console</a\>

RECOVERY

attributes.moreInfo=\<a href="http://x.x.x.x/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.RECOVERY.ID}">Zabbix console</a\>

Troubleshooting
---------------

Set the debug level to `4`, restart the zabbix server and tail the server
logs:

    $ vi /etc/zabbix/zabbix_server.conf
    DebugLevel=4

    $ tail -f /var/log/zabbix/zabbix_server.log

See the [PagerDuty guide](http://www.pagerduty.com/docs/guides/zabbix-integration-guide/)
to configuring Zabbix integrations for an example installation with
screenshots.

References
----------

  * Zabbix Custom Alert Scripts: https://www.zabbix.com/documentation/current/manual/config/notifications/media/script
  * Zabbix Custom User Macros: https://www.zabbix.com/documentation/current/manual/config/macros/usermacros

License
-------

Copyright (c) 2013-2019 Nick Satterly. Available under the MIT License.
