import unittest
from unittest.mock import MagicMock

from safecast_deploy.aws_state import AwsTierType, EnvType
from safecast_deploy.config_saver import ConfigSaver
from safecast_deploy.result_logger import ResultLogger


class TestConfigSaver(unittest.TestCase):
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

    def test_run_success_single_tier(self):
        eb_client = MagicMock()
        eb_client.describe_environments = MagicMock(return_value=self.envs_return)
        result_logger = ResultLogger(log_git=False)
        ConfigSaver(eb_client, result_logger).run(
            app='testapp', env=EnvType.DEV, tier=AwsTierType.WEB,
        )

    def test_run_success_unqualified(self):
        eb_client = MagicMock()
        eb_client.describe_environments = MagicMock(return_value=self.envs_return)
        result_logger = ResultLogger(log_git=False)
        ConfigSaver(eb_client, result_logger).run(app='testapp')
