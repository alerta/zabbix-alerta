#!/usr/bin/env python
"""
    zac: Zabbix-Alerta Configurator
"""

import argparse
import getpass
import logging
import os
import sys
import time
from datetime import datetime

import protobix
from alertaclient.api import Client
from pyzabbix import ZabbixAPI, ZabbixAPIException

try:
    import configparser
except ImportError:
    import ConfigParser as configparser



__version__ = '3.5.1'

OPTIONS = {
    'config_file': '~/.alerta.conf',
    'profile': None,
    'endpoint': 'http://localhost:8080',
    'key': '',
    'sslverify': True,
    'debug': False,
}

epilog = """Note

  To use zabbix severity levels you must update the Alerta server
  and web config files as well. See online documentation for more info
  https://github.com/alerta/zabbix-alerta#advanced-configuration

Example

  $ zac --server http://zabbix-web --trapper zabbix-server -w http://alerta:8080/api

"""

# media type
EMAIL = 0
SCRIPT = 1
SMS = 2
JABBER = 3
EZ_TEXTING = 100

# use if severity
NIWAHD = 63

# status
ENABLED = 0
DISABLED = 1

# eventsource
TRIGGERS = 0

# operation type
SEND_MESSAGE = 0

# default msg
USE_DATA_FROM_OPERATION = 0
USE_DATA_FROM_ACTION = 1

# maintenance mode
DO_NOT_PAUSE_EXEC = 0
PAUSE_EXECUTION = 1

# host
DEFAULT = 1
AGENT = 1

CONNECT_USING_DNS = 0
CONNECT_USING_IP = 1

# item type
ZABBIX_TRAPPER = 2

# item value type
TEXT = 4

# priority
NOT_CLASSIFIED = 0
INFORMATION = 1
WARNING = 2
AVERAGE = 3
HIGH = 4
DISASTER = 5

# trigger type
DO_NOT_GENERATE_MULTIPLE_EVENTS = 0
GENERATE_MULTIPLE_EVENTS = 1

# manual close
NO_MANUAL_CLOSE = 0
ALLOW_MANUAL_CLOSE = 1


class ZabbixConfig:
    def __init__(self, endpoint, user, password=''):

        self.zapi = ZabbixAPI(endpoint)
        self.zapi.login(user, password)
        print('Connected to Zabbix API Version %s' % self.zapi.api_version())

        self.item_id = None
        self.trigger_id = None

    def create_action(self, sendto, web_url, use_zabbix_severity=False):

        use_console_link = True

        medias = self.zapi.mediatype.get(output='extend')
        try:
            media_id = [m for m in medias if m['description'] == 'Alerta'][0]['mediatypeid']
        except Exception:
            print('media does not exist. creating...')
            response = self.zapi.mediatype.create(
                type=SCRIPT,
                description='Alerta',
                exec_path='zabbix-alerta',
                exec_params='{ALERT.SENDTO}\n{ALERT.SUBJECT}\n{ALERT.MESSAGE}\n',
                maxattempts='5',
                attempt_interval='5s',
            )
            media_id = response['mediatypeids'][0]

        users = self.zapi.user.get(output='extend')
        admin_user_id = [u for u in users if u['alias'] == 'Admin'][0]['userid']

        media_alerta = {
            'mediatypeid': media_id,
            'sendto': sendto,
            'active': ENABLED,
            'severity': NIWAHD,
            'period': '1-7,00:00-24:00',
        }

        try:
            self.zapi.user.updatemedia(users={'userid': admin_user_id}, medias=media_alerta)
        except ZabbixAPIException as e:
            sys.exit(e)

        default_message = (
            'resource={HOST.NAME1}\r\n'
            'event={ITEM.KEY1}\r\n'
            'environment=Production\r\n'
            'severity={TRIGGER.SEVERITY}' + ('!!' if use_zabbix_severity else '') + '\r\n'
            'status={TRIGGER.STATUS}\r\n'
            'ack={EVENT.ACK.STATUS}\r\n'
            'service={TRIGGER.HOSTGROUP.NAME}\r\n'
            'group=Zabbix\r\n'
            'value={ITEM.VALUE1}\r\n'
            'text={TRIGGER.STATUS}: {TRIGGER.NAME}\r\n'
            'tags={EVENT.TAGS}\r\n'
            'attributes.ip={HOST.IP1}\r\n'
            'attributes.thresholdInfo={TRIGGER.TEMPLATE.NAME}: {TRIGGER.EXPRESSION}\r\n'
            'attributes.eventId={EVENT.ID}\r\n'
            'attributes.triggerId={TRIGGER.ID}\r\n'
            'type=zabbixAlert\r\n'
            'dateTime={EVENT.DATE}T{EVENT.TIME}Z\r\n'
        )

        operations_console_link = (
            'attributes.moreInfo=<a href="%s/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.ID}" target="_blank">Zabbix console</a>'
            % web_url
        )
        operations = {
            'operationtype': SEND_MESSAGE,
            'opmessage': {
                'default_msg': USE_DATA_FROM_OPERATION,
                'mediatypeid': media_id,
                'subject': '{TRIGGER.STATUS}: {TRIGGER.NAME}',
                'message': default_message + operations_console_link if use_console_link else '',
            },
            'opmessage_usr': [{'userid': admin_user_id}],
        }

        recovery_console_link = (
            'attributes.moreInfo=<a href="%s/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.RECOVERY.ID}" target="_blank">Zabbix console</a>'
            % web_url
        )
        recovery_operations = {
            'operationtype': SEND_MESSAGE,
            'opmessage': {
                'default_msg': USE_DATA_FROM_OPERATION,
                'mediatypeid': media_id,
                'subject': '{TRIGGER.STATUS}: {TRIGGER.NAME}',
                'message': default_message + recovery_console_link if use_console_link else '',
            },
            'opmessage_usr': [{'userid': admin_user_id}],
        }

        try:
            self.zapi.action.create(
                name='Forward to Alerta',
                eventsource=TRIGGERS,
                status=ENABLED,
                esc_period=120,
                def_shortdata='{TRIGGER.NAME}: {TRIGGER.STATUS}',
                def_longdata=default_message,
                r_shortdata='{TRIGGER.NAME}: {TRIGGER.STATUS}',
                r_longdata=default_message,
                maintenance_mode=DO_NOT_PAUSE_EXEC,
                operations=[operations],
                recovery_operations=[recovery_operations],
            )
        except ZabbixAPIException as e:
            print(e)

    def test_action(self, trapper, endpoint, key=None):

        hosts = self.zapi.host.get()
        zabbix_server_id = [h for h in hosts if h['name'] == 'Zabbix server'][0]['hostid']

        # enable zabbix server monitoring
        self.zapi.host.update(hostid=zabbix_server_id, status=ENABLED)

        description = 'Test trigger event on {HOST.NAME}'
        try:
            response = self.zapi.item.create(
                name='Test Zabbix-Alerta Integration',
                type=ZABBIX_TRAPPER,
                key_='test.alerta',
                value_type=TEXT,
                hostid=zabbix_server_id,
                status=ENABLED,
            )
            self.item_id = response['itemids'][0]

            response = self.zapi.trigger.create(
                hostid=zabbix_server_id,
                description=description,
                expression='{Zabbix server:test.alerta.diff()}>0',
                type=GENERATE_MULTIPLE_EVENTS,
                priority=INFORMATION,
                status=ENABLED,
                manual_close=ALLOW_MANUAL_CLOSE,
            )
            self.trigger_id = response['triggerids'][0]
        except ZabbixAPIException:
            triggers = self.zapi.trigger.get(hostids=zabbix_server_id)
            self.trigger_id = [t for t in triggers if t['description'] == description][0]['triggerid']
            self.item_id = self.zapi.item.get(triggerids=self.trigger_id)[0]['itemid']

        def zabbix_send(value):
            cfg = protobix.ZabbixAgentConfig()
            cfg.server_active = trapper
            zbx = protobix.DataContainer(cfg)

            zbx.data_type = 'items'
            zbx.add_item(host='Zabbix server', key='test.alerta', value=value)
            response = zbx.send()
            print(response)

        print('sending test items')
        now = int(time.time())
        zabbix_send('OK')

        print('wait for items to be received')
        count = 0
        while True:
            count += 1
            response = self.zapi.history.get(
                itemids=[self.item_id],
                history=TEXT,
                time_from=now,
                output='extend',
                sortfield='clock',
                sortorder='DESC',
                limit=10,
            )
            zabbix_send('RETRY%s' % count)
            if len(response) > 1:
                break
            print('waiting 5 seconds...')
            time.sleep(5)

        print('sent items received by zabbix')
        print(response)

        from_date = datetime.utcnow().replace(microsecond=0).isoformat() + '.000Z'

        print('wait for triggered event')
        while True:
            response = self.zapi.event.get(
                objectids=self.trigger_id,
                time_from=now,
                output='extend',
                sortfield=['clock', 'eventid'],
                sortorder='DESC',
            )
            if len(response) > 0 and 'eventid' in response[0]:
                event_id = response[0]['eventid']
                break
            print('waiting 2 seconds...')
            time.sleep(2)

        print('event triggered')
        print(response[0])

        print('wait for alert')
        while True:
            response = self.zapi.alert.get(
                eventid=event_id,
                time_from=now,
                output='extend',
            )
            if len(response) > 0:
                break
            print('waiting 2 seconds...')
            time.sleep(2)

        print('alert triggered by event')
        print(response[0])

        api = Client(endpoint, key)

        print('check alert received by Alerta')
        while True:
            try:
                response = api.get_alerts(query=[('event', 'test.alerta'), ('from-date', from_date)])
            except Exception as e:
                sys.exit(e)
            if len(response) > 0:
                break
            time.sleep(5)
        print(response[0].last_receive_id)

        print('success!')

    def clean_up(self):

        try:
            self.zapi.trigger.delete(self.trigger_id)
            self.zapi.item.delete(self.item_id)
        except ZabbixAPIException:
            pass


def main():

    config_file = os.environ.get('ALERTA_CONF_FILE') or OPTIONS['config_file']

    config = configparser.RawConfigParser(defaults=OPTIONS)
    try:
        config.read(os.path.expanduser(config_file))
    except Exception:
        sys.exit('Problem reading configuration file %s - is this an ini file?' % config_file)

    parser = argparse.ArgumentParser(
        prog='zac',
        usage='zac [OPTIONS] SENDTO',
        description='Zabbix-Alerta configuration script',
        epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument('--server', default='http://localhost', help='Zabbix web API URL (default: http://localhost)')
    parser.add_argument('--user', default='Admin', help='Zabbix admin user (default: "Admin")')
    parser.add_argument(
        '--no-password', '-w', action='store_true', help='do not prompt for password (default: "zabbix")'
    )
    parser.add_argument('--trapper', default='localhost', help='Zabbix trapper host (default: localhost)')
    parser.add_argument('--zabbix-severity', '-Z', action='store_true', help='use Zabbix severity levels')
    parser.add_argument('--debug', action='store_true', help='print debug output')
    parser.add_argument('sendto', help='config profile or alerta API endpoint and key')
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
        # debug logging
        stream = logging.StreamHandler(sys.stdout)
        stream.setLevel(logging.DEBUG)
        log = logging.getLogger('pyzabbix')
        log.addHandler(stream)
        log.setLevel(logging.DEBUG)

    if args.no_password:
        password = 'zabbix'  # default for 'Admin'
    else:
        password = getpass.getpass()

    try:
        zc = ZabbixConfig(args.server, args.user, password)

        # configure action
        zc.create_action(args.sendto, args.server, args.zabbix_severity)

        # test action
        zc.test_action(args.trapper, args.endpoint, args.key)

        # clean up ?
        # zc.clean_up()

    except (SystemExit, KeyboardInterrupt):
        sys.exit(0)
    except Exception as e:
        sys.exit(e)


if __name__ == '__main__':
    main()
