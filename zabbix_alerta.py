#!/usr/bin/env python
"""
    zabbix-alerta: Forward Zabbix events to Alerta
"""

import configparser
import os

import click
from alertaclient.api import Client

__version__ = '4.0.0'

default_config = {
    'config_file': '~/.alerta.conf',
    'profile': None,
    'endpoint': 'http://localhost:8080',
    'key': '',
    'timeout': 5.0,
    'sslverify': True,
    'debug': False,
}

ZBX_SEVERITY_MAP = {
    'Disaster': 'critical',
    'High': 'major',
    'Average': 'minor',
    'Warning': 'warning',
    'Information': 'informational',
    'Not classified': 'indeterminate',
}


def parse_zabbix(subject, message):

    alert = {}
    attributes = {}
    zabbix_severity = False
    for line in message.split('\n'):
        if '=' not in line:
            continue
        try:
            macro, value = line.rstrip().split('=', 1)
        except ValueError as e:
            click.secho('{}: {}'.format(e, line))
            continue

        if macro == 'service':
            value = value.split(',')
        elif macro == 'severity':
            if value.endswith('!!'):
                zabbix_severity = True
                value = value.replace('!!', '')
            else:
                value = ZBX_SEVERITY_MAP.get(value, 'indeterminate')
        elif macro == 'timeout':
            value = int(value)
        elif macro == 'tags':
            value = value.split(',')
        elif macro.startswith('attributes.'):
            attributes[macro.replace('attributes.', '')] = value

        alert[macro] = value
        click.echo('{} -> {}'.format(macro, value))

    # if {$ENVIRONMENT} user macro isn't defined anywhere set default
    if alert.get('environment', '') == '{$ENVIRONMENT}':
        alert['environment'] = 'Production'

    zabbix_status = alert.pop('status', None)

    if zabbix_status == 'OK':
        if zabbix_severity:
            alert['severity'] = 'ok'
        else:
            alert['severity'] = 'normal'

    if alert.pop('ack', '') == 'Yes' and zabbix_status != 'OK':
        alert['status'] = 'ack'

    alert['attributes'] = attributes
    alert['origin'] = 'zabbix/%s' % os.uname()[1]
    alert['rawData'] = '{}\n\n{}'.format(subject, message)

    return alert


CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.command('zabbix-alerta', context_settings=CONTEXT_SETTINGS)
@click.argument('sendto')
@click.argument('summary')
@click.argument('body')
def cli(sendto, summary, body):
    """
        Zabbix-to-Alerta integration script

    INSTALL

       $ ln -s `which zabbix-alerta` <AlertScriptsPath>

    ALERT FORMAT

    OPERATIONS

    Default subject:

    {TRIGGER.STATUS}: {TRIGGER.NAME}

    Default message:

    \b
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
    attributes.eventId={EVENT.ID}
    attributes.triggerId={TRIGGER.ID}
    attributes.ip={HOST.IP1}
    attributes.thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}
    attributes.moreInfo=<a href="http://x.x.x.x/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.ID}">Zabbix console</a>
    type=zabbixAlert
    dateTime={EVENT.DATE}T{EVENT.TIME}Z

    RECOVERY

    Default subject:

    {TRIGGER.STATUS}: {TRIGGER.NAME}

    Default message:

    \b
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
    """

    # FIXME - use {ITEM.APPLICATION} for alert "group" when ZBXNEXT-2684 is resolved (see https://support.zabbix.com/browse/ZBXNEXT-2684)

    click.echo('[alerta] Sending message "{}" to {}...'.format(summary, sendto))

    options = default_config
    parser = configparser.RawConfigParser(defaults=options)

    options['config_file'] = os.environ.get('ALERTA_CONF_FILE') or options['config_file']
    parser.read(os.path.expanduser(options['config_file']))

    # sendto=apiUrl[;key]
    if sendto.startswith('http://') or sendto.startswith('https://'):
        want_profile = None
        try:
            options['endpoint'], options['key'] = sendto.split(';', 1)
        except ValueError:
            options['endpoint'] = sendto
    # sendto=profile
    else:
        want_profile = sendto or os.environ.get('ALERTA_DEFAULT_PROFILE') or parser.defaults().get('profile')

        if want_profile and parser.has_section('profile %s' % want_profile):
            for opt in options:
                try:
                    options[opt] = parser.getboolean('profile %s' % want_profile, opt)
                except (ValueError, AttributeError):
                    options[opt] = parser.get('profile %s' % want_profile, opt)
        else:
            for opt in options:
                try:
                    options[opt] = parser.getboolean('DEFAULT', opt)
                except (ValueError, AttributeError):
                    options[opt] = parser.get('DEFAULT', opt)

    options['profile'] = want_profile
    options['endpoint'] = os.environ.get('ALERTA_ENDPOINT', options['endpoint'])
    options['key'] = os.environ.get('ALERTA_API_KEY', options['key'])

    api = Client(
        endpoint=options['endpoint'], key=options['key'], timeout=options['timeout'], ssl_verify=options['sslverify']
    )

    try:
        alert = parse_zabbix(summary, body)
        api.send_alert(**alert)
    except Exception as e:
        click.secho('ERROR: {}'.format(e))
        raise click.Abort()

    click.echo('Successfully sent message "{}" to {}!'.format(summary, options['endpoint']))


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
