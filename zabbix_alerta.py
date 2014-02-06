#!/usr/bin/env python

import os
import sys
import argparse
import json
import urllib2

import logging as LOG

__version__ = '0.2.1'

_DEFAULT_LOG_FORMAT = "%(asctime)s.%(msecs).03d %(name)s[%(process)d] %(threadName)s %(levelname)s - %(message)s"
_DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

dry_run = False

ZBX_SEVERITY_MAP = {
    'Disaster':       'critical',
    'High':           'major',
    'Average':        'minor',
    'Warning':        'warning',
    'Information':    'informational',
    'Not classified': 'unknown',
}


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("endpoint", help="alerta API URL endpoint")
    parser.add_argument("summary", help="alert summary")
    parser.add_argument("body", help="alert body")
    args = parser.parse_args()

    LOG.debug(args.endpoint)
    LOG.debug(args.summary)
    LOG.debug(args.body)

    api_url = "%s/alerta/api/v2/alerts/alert.json" % args.endpoint

    alert = dict()
    alert['summary'] = args.summary
    alert['origin'] = 'zabbix/%s' % os.uname()[1]
    alert['rawData'] = args.body

    for line in args.body.split('\n'):
        if '=' not in line:
            continue
        try:
            macro, value = line.split('=', 1)
        except ValueError, e:
            LOG.warning('%s: %s', e, line)
            continue

        if macro in ['environment', 'service']:
            value = value.split(', ')
        if macro == 'severity':
            value = ZBX_SEVERITY_MAP.get(value, 'unknown')
        if macro == 'tags':
            value = dict([tag.split('=') for tag in value.split(',')])

        alert[macro] = value
        LOG.debug('%s -> %s', macro, value)

    if 'status' in alert and alert['status'] == 'OK':
        alert['severity'] = 'normal'
        del alert['status']

    if 'ack' in alert:
        if alert['ack'] == 'Yes':
            alert['status'] = 'ack'
        del alert['ack']

    LOG.info(alert)

    post = json.dumps(alert, ensure_ascii=False)
    headers = {'Content-Type': 'application/json'}

    request = urllib2.Request(api_url, headers=headers)
    request.add_data(post)
    LOG.debug('url=%s, data=%s, headers=%s', request.get_full_url(), request.data, request.headers)

    if dry_run:
        print "curl '%s' -H 'Content-Type: application/json' -d '%s'" % (api_url, post)
        sys.exit(0)

    LOG.debug('Sending alert to API endpoint...')
    try:
        response = urllib2.urlopen(request, post, 15)
    except ValueError, e:
        LOG.error('Could not send alert to API endpoint %s : %s', api_url, e)
        sys.exit(1)
    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            error = str(e.reason)
        elif hasattr(e, 'code'):
            error = e.code
        else:
            error = 'Unknown Send Error'
        LOG.error('Could not send to API endpoint %s : %s', api_url, error)
        sys.exit(2)
    else:
        code = response.getcode()
    LOG.info('Alert sent to API endpoint %s : status=%s', api_url, code)

    try:
        data = json.loads(response.read())
    except Exception, e:
        LOG.error('Error with response from API endpoint %s : %s', api_url, e)
        sys.exit(3)

    LOG.debug('Response from API endpoint: %s', data)


if __name__ == '__main__':

    LOG.basicConfig(filename="/var/log/zabbix/zabbix_alerta.log", format=_DEFAULT_LOG_FORMAT, datefmt=_DEFAULT_LOG_DATE_FORMAT, level=LOG.DEBUG)
    main()

