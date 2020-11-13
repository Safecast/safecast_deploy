import datetime
import sys
import unittest
from unittest.mock import MagicMock

from safecast_deploy.aws_state import AwsTierType, EnvType
from safecast_deploy.state import State


class TestState(unittest.TestCase):
    envs_return = {
            'Environments': [
                {
                    'EnvironmentName': 'safecasttestapp-dev-021',
                    'EnvironmentId': '1248234',
                    'ApplicationName': 'testapp',
                    'VersionLabel': 'api-unit_test-125-6b69384109c6f3348ccaf4d5e761808f710bd6a9',
                    'PlatformArn': 'test-arn',
                    'TemplateName': 'test-template',
                    'Status': 'Ready',
                    'Health': 'Green',
                    'HealthStatus': 'Ok',
                },
            ],
        }

    versions_return = {
        'ApplicationVersions': [
            {
                'VersionLabel': 'api-unit_test-126-6b69384109c6f3348ccaf4d5e761808f821bd6a9',
                'DateUpdated': datetime.datetime(2020, 1, 1),
                'Status': 'Unprocessed'
            },
        ],
    }

    def test_new_version(self):
        eb_client = MagicMock()
        eb_client.describe_environments = MagicMock(return_value=self.envs_return)
        eb_client.describe_application_versions = MagicMock(return_value=self.versions_return)
        new_state = State('testapp', eb_client).new_aws_state(EnvType.DEV, new_version='api-unit_test-126-6b69384109c6f3348ccaf4d5e761808f821bd6a9')
        self.assertEqual(new_state.envs[EnvType.DEV][AwsTierType.WEB].num, 21)
        print(new_state, file=sys.stderr)

    def test_new_arn(self):
        eb_client = MagicMock()
        eb_client.describe_environments = MagicMock(return_value=self.envs_return)
        eb_client.describe_application_versions = MagicMock(return_value=self.versions_return)
        new_state = State('testapp', eb_client).new_aws_state(EnvType.DEV, new_arn='new-test-arn')
        self.assertEqual(new_state.envs[EnvType.DEV][AwsTierType.WEB].num, 22)
        print(new_state, file=sys.stderr)

    def test_new_arn_version(self):
        eb_client = MagicMock()
        eb_client.describe_environments = MagicMock(return_value=self.envs_return)
        eb_client.describe_application_versions = MagicMock(return_value=self.versions_return)
        new_state = State('testapp', eb_client).new_aws_state(
            EnvType.DEV,
            new_version='api-unit_test-126-6b69384109c6f3348ccaf4d5e761808f821bd6a9',
            new_arn='new-test-arn'
        )
        self.assertEqual(new_state.envs[EnvType.DEV][AwsTierType.WEB].num, 22)
        print(new_state, file=sys.stderr)
