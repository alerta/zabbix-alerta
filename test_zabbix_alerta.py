import textwrap
import unittest
from types import SimpleNamespace

import requests_mock
from click.testing import CliRunner

from zabbix_alerta import cli, parse_zabbix

SUMMARY_TEMPLATE = '''{TRIGGER.STATUS}: {TRIGGER.NAME}'''
BODY_TEMPLATE = '''
    resource={HOST.NAME1}
    event={ITEM.KEY1}
    environment=Production
    severity={TRIGGER.SEVERITY}!!
    status={TRIGGER.STATUS}
    ack={EVENT.ACK_STATUS}
    service={TRIGGER.HOSTGROUP_NAME}
    group=Zabbix
    value={ITEM.VALUE1}
    text={TRIGGER.STATUS}: {TRIGGER.NAME}
    tags={EVENT.TAGS}
    attributes.ip={HOST.IP1}
    attributes.thresholdInfo={TRIGGER.TEMPLATE_NAME}: {TRIGGER.EXPRESSION}
    attributes.moreInfo=<a href="http://x.x.x.x/tr_events.php?triggerid={TRIGGER.ID}&eventid={EVENT.ID}">Zabbix console</a>
    type=zabbixAlert
    dateTime={EVENT.DATE}T{EVENT.TIME}Z
'''

trigger = {
    'ID': 1,
    'STATUS': 'PROBLEM',
    'NAME': 'PSU-0.40: Temperature is above threshold',
    'SEVERITY': 'warning',
    'TEMPLATE_NAME': 'template',
    'EXPRESSION': 'expr',
    'HOSTGROUP_NAME': 'group1',
}
host = {'NAME1': 'hostname1', 'IP1': '10.1.1.1'}
item = {'KEY1': 'e4597efc-3811-4476-9cf5-4e9d8501037e', 'VALUE1': '61°'}
event = {'ID': 2, 'DATE': '2018.01.02', 'TIME': '13:04:30', 'ACK_STATUS': '', 'TAGS': 'tag1,tag2'}

summary = SUMMARY_TEMPLATE.format(TRIGGER=SimpleNamespace(**trigger))
body = textwrap.dedent(
    BODY_TEMPLATE.format(
        HOST=SimpleNamespace(**host),
        ITEM=SimpleNamespace(**item),
        TRIGGER=SimpleNamespace(**trigger),
        EVENT=SimpleNamespace(**event),
    )
)


class SenderTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self.runner = CliRunner(echo_stdin=True)

    def tearDown(self) -> None:
        pass

    @requests_mock.mock()
    def test_cli(self, m):

        self.maxDiff = None

        m.post('http://localhost:8080/alert', text='{"status":"ok"}')

        result = self.runner.invoke(cli, ['http://localhost:8080', summary, body])
        self.assertEqual(
            result.output,
            '[alerta] Sending message "PROBLEM: PSU-0.40: Temperature is above threshold" to http://localhost:8080...\n'
            + 'resource -> hostname1\n'
            + 'event -> e4597efc-3811-4476-9cf5-4e9d8501037e\n'
            + 'environment -> Production\n'
            + 'severity -> warning\n'
            + 'status -> PROBLEM\n'
            + 'ack -> \n'
            'service -> [\'group1\']\n'
            + 'group -> Zabbix\n'
            + 'value -> 61°\n'
            + 'text -> PROBLEM: PSU-0.40: Temperature is above threshold\n'
            + 'tags -> [\'tag1\', \'tag2\']\n'
            + 'attributes.ip -> 10.1.1.1\n'
            + 'attributes.thresholdInfo -> template: expr\n'
            + 'attributes.moreInfo -> <a href="http://x.x.x.x/tr_events.php?triggerid=1&eventid=2">Zabbix console</a>\n'
            + 'type -> zabbixAlert\n'
            + 'dateTime -> 2018.01.02T13:04:30Z\n'
            + 'Successfully sent message "PROBLEM: PSU-0.40: Temperature is above threshold" to http://localhost:8080!\n'
        )
        # self.assertEqual(
        #     result.stderr,
        #     ''
        # )

    def test_parser(self):

        alert = parse_zabbix(summary, body)

        assert alert['resource'] == 'hostname1'
        assert alert['event'] == 'e4597efc-3811-4476-9cf5-4e9d8501037e'
        assert alert['environment'] == 'Production'
        assert alert['severity'] == 'warning'
        assert alert['service'] == ['group1']
        assert alert['group'] == 'Zabbix'
        assert alert['value'] == '61°'
        assert alert['text'] == 'PROBLEM: PSU-0.40: Temperature is above threshold'
        # assert alert['tags'] == ['tag1', 'tag2']
        assert alert['attributes'] == {
            'ip': '10.1.1.1',
            'moreInfo': '<a href="http://x.x.x.x/tr_events.php?triggerid=1&eventid=2">Zabbix console</a>',
            'thresholdInfo': 'template: expr',
        }
        assert alert['origin'].startswith('zabbix/')
        assert alert['type'] == 'zabbixAlert'
