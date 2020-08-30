import getpass
import json
import os
import re
import urllib

import sys
from urllib.parse import urlparse

from safecast_deploy import state


def run_cli(args):
    if 'GRAFANA_API_KEY' in os.environ:
        grafana_api_key = os.environ['GRAFANA_API_KEY']
    else:
        grafana_api_key = getpass.getpass('Enter the Grafana API key (will not be echoed): ')
    GrafanaUpdater(args.app, grafana_api_key).run()


class GrafanaUpdater:
    def __init__(self, app, grafana_api_key):
        self.state = state.State(app)
        self.grafana_api_key = grafana_api_key
        if app == 'api':
            self.dashboard_uid = 'W7c552kZz'
        elif app == 'ingest':
            self.dashboard_uid = 'MoVFmrdZz'

    def run(self):
        c = self.state.eb_client

        dashboard = self._get_dashboard()

        metadata = self.state.env_metadata['prd']
        env_resources = metadata['api_resources']
        self._update_key(dashboard, 'LoadBalancerName', env_resources['LoadBalancers'][0]['Name'])
        self._update_key(
            dashboard,
            'AutoScalingGroupName',
            env_resources['AutoScalingGroups'][0]['Name'],
            parent_title_pattern=re.compile(r'.*(web CPU|web network)')
        )

        metadata = self.state.env_metadata['prd-wrk']
        env_resources = metadata['api_resources']
        self._update_key(
            dashboard,
            'AutoScalingGroupName',
            env_resources['AutoScalingGroups'][0]['Name'],
            parent_title_pattern=re.compile(r'(Worker CPU|Worker Network)')
        )

        queue_url = [q['URL'] for q in env_resources['Queues'] if q['Name'] == 'WorkerQueue'][0]
        queue_name = urlparse(queue_url).path.split('/')[-1]
        self._update_key(
            dashboard,
            'QueueName',
            queue_name
        )

        self._push_dashboard(dashboard)

    def _get_dashboard(self):
        req = urllib.request.Request(
            f'https://grafana.safecast.cc/api/dashboards/uid/{self.dashboard_uid}',
            headers={
                'Authorization': f'Bearer {self.grafana_api_key}',
            }
        )
        res = urllib.request.urlopen(req)
        if res.getcode() != 200:
            print('ERROR: Could not fetch the dashboard; HTTP status code was ' + res.getcode(), file=sys.stderr)
            exit(1)
        return json.loads(res.read())['dashboard']

    def _push_dashboard(self, dashboard):
        req_body = {
            'dashboard': dashboard,
            'folderId': 37,
        }
        req_body_data = bytearray(json.dumps(req_body), 'utf-8')
        req = urllib.request.Request(
            f'https://grafana.safecast.cc/api/dashboards/db',
            data=req_body_data,
            headers={
                'Authorization': f'Bearer {self.grafana_api_key}',
                'Content-Type': 'application/json; charset=utf-8',
            },
            method='POST',
        )
        res = urllib.request.urlopen(req)
        if res.getcode() != 200:
            print('ERROR: Could not fetch the dashboard; HTTP status code was ' + res.getcode(), file=sys.stderr)
            exit(1)

    def _update_key(self, obj, key, value, parent_title_pattern=None, in_panel=False):
        if parent_title_pattern is None:
            in_panel = True
        if isinstance(obj, list):
            for item in obj:
                self._update_key(item, key, value, parent_title_pattern, in_panel)
        elif isinstance(obj, dict):
            if parent_title_pattern is not None and 'title' in obj:
                in_panel = bool(parent_title_pattern.match(obj['title']))
            for curr_key in obj:
                if in_panel and curr_key == key:
                    obj[curr_key] = value
                else:
                    self._update_key(obj[curr_key], key, value, parent_title_pattern, in_panel)
