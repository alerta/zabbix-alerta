#!/usr/bin/env python
"""
    zabbix-alerta: Forward Zabbix events to Alerta
"""

import os
import sys
import argparse
import logging as LOG

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from alertaclient.api import ApiClient
from alertaclient.alert import Alert

__version__ = '3.2.0'

LOG_FILE = '/var/log/zabbix/zabbix_alerta.log'
LOG_FORMAT = "%(asctime)s.%(msecs).03d %(name)s[%(process)d] %(threadName)s %(levelname)s - %(message)s"
LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"

OPTIONS = {
    'config_file': '~/.alerta.conf',
    'profile':     None,
    'endpoint':    'http://localhost:8080',
    'key':         '',
    'sslverify':   True,
    'debug':       False
}

ZBX_SEVERITY_MAP = {
    'Disaster':       'critical',
    'High':           'major',
    'Average':        'minor',
    'Warning':        'warning',
    'Information':    'informational',
    'Not classified': 'indeterminate'
}

epilog = '''INSTALL

   $ ln -s `which zabbix-alerta` <AlertScriptsPath>

ALERT FORMAT

OPERATIONS

Default subject:
{TRIGGER.STATUS}: {TRIGGER.NAME}

Default message:
resource={HOST.NAME1}
event={ITEM.KEY1}
environment=Production
severity={TRIGGER.SEVERITY}!!
status={TRIGGER.STATUS}
ack={EVENT.ACK.STATUS}
service={TRIGGER.HOSTGROUP.NAME}
group=Zabbix
value={ITEM.VALUE1}
text={TRIGGER.STATUS}: {TRIGGER.NAME}
tags={EVENT.TAGS}
attributes.ip={HOST.IP1}
attributes.thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}
attributes.moreInfo=<a href="http://x.x.x.x/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.ID}">Zabbix console</a>
type=zabbixAlert
dateTime={EVENT.DATE}T{EVENT.TIME}Z

RECOVERY

Default subject:
{TRIGGER.STATUS}: {TRIGGER.NAME}

Default message:
resource={HOST.NAME1}
event={ITEM.KEY1}
environment=Production
severity={TRIGGER.SEVERITY}!!
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



'''

# FIXME - use {ITEM.APPLICATION} for alert "group" when ZBXNEXT-2684 is resolved (see https://support.zabbix.com/browse/ZBXNEXT-2684)

def parse_zabbix(subject, message, **kwargs):

    alert = {}
    attributes = {}
    zabbix_severity = False
    for line in message.split('\n'):
        if '=' not in line:
            continue
        try:
            macro, value = line.rstrip().split('=', 1)
        except ValueError as e:
            LOG.warning('%s: %s', e, line)
            continue

        if macro == 'service':
            value = value.split(', ')
        elif macro == 'severity':
            if value.endswith('!!'):
                zabbix_severity = True
                value = value.replace('!!','')
            else:
                value = ZBX_SEVERITY_MAP.get(value, 'indeterminate')
        elif macro == 'tags':
            value = value.split(', ')
        elif macro.startswith('attributes.'):
            attributes[macro.replace('attributes.', '')] = value

        alert[macro] = value
        LOG.debug('%s -> %s', macro, value)

    # if {$ENVIRONMENT} user macro isn't defined anywhere set default
    if alert['environment'] == '{$ENVIRONMENT}':
        alert['environment'] = 'Production'

    if 'status' in alert:
        if alert['status'].startswith('OK'):
            if zabbix_severity:
                alert['severity'] = 'ok'
            else:
                alert['severity'] = 'normal'
        del alert['status']

    if 'ack' in alert:
        if alert['ack'] == 'Yes':
            alert['status'] = 'ack'
        del alert['ack']

    alert['attributes'] = attributes
    alert['origin'] = "zabbix/%s" % os.uname()[1]
    alert['rawData'] = "%s\n\n%s" % (subject, message)

    return Alert(**alert)


def main():

    config_file = os.environ.get('ALERTA_CONF_FILE') or OPTIONS['config_file']

    config = configparser.RawConfigParser(defaults=OPTIONS)
    try:
        config.read(os.path.expanduser(config_file))
    except Exception:
        sys.exit("Problem reading configuration file %s - is this an ini file?" % config_file)

    parser = argparse.ArgumentParser(
        prog='zabbix-alerta',
        usage='zabbix-alerta SENDTO SUMMARY BODY',
        description='Zabbix-to-Alerta integration script',
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'sendto',
        help='config profile or alerta API endpoint and key'
    )
    parser.add_argument(
        'summary',
        help='alert summary'
    )
    parser.add_argument(
        'body',
        help='alert body (see format below)'
    )
    args, left = parser.parse_known_args()

    # sendto=apiUrl[;key]
    if args.sendto.startswith('http://') or args.sendto.startswith('https://'):
        want_profile = None
        try:
            OPTIONS['endpoint'], OPTIONS['key'] = args.sendto.split(';', 1)
        except ValueError:
            OPTIONS['endpoint'] = args.sendto
    # sendto=profile
    else:
        want_profile = args.sendto or os.environ.get('ALERTA_DEFAULT_PROFILE') or config.defaults().get('profile')

        if want_profile and config.has_section('profile %s' % want_profile):
            for opt in OPTIONS:
                try:
                    OPTIONS[opt] = config.getboolean('profile %s' % want_profile, opt)
                except (ValueError, AttributeError):
                    OPTIONS[opt] = config.get('profile %s' % want_profile, opt)
        else:
            for opt in OPTIONS:
                try:
                    OPTIONS[opt] = config.getboolean('DEFAULT', opt)
                except (ValueError, AttributeError):
                    OPTIONS[opt] = config.get('DEFAULT', opt)

    parser.set_defaults(**OPTIONS)
    args = parser.parse_args()

    if args.debug:
        LOG.basicConfig(stream=sys.stderr, format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=LOG.DEBUG)
    else:
        LOG.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, datefmt=LOG_DATE_FMT, level=LOG.INFO)

    LOG.info("[alerta] endpoint=%s key=%s", args.endpoint, args.key)
    api = ApiClient(endpoint=args.endpoint, key=args.key, ssl_verify=args.sslverify)

    LOG.debug("[alerta] sendto=%s, summary=%s, body=%s", args.sendto, args.summary, args.body)
    try:
        alert = parse_zabbix(args.summary, args.body)
        api.send(alert)
    except (SystemExit, KeyboardInterrupt):
        LOG.warning("Exiting zabbix-alerta.")
        sys.exit(0)
    except Exception as e:
        LOG.error(e, exc_info=1)
        sys.exit(1)

if __name__ == '__main__':

    main()
