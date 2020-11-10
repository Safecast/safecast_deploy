import unittest
from unittest.mock import MagicMock

import boto3

from safecast_deploy.aws_state import AwsState, AwsTier, AwsTierType, EnvType, ParsedVersion
from safecast_deploy.result_logger import ResultLogger
from safecast_deploy.same_env import SameEnv


class TestSameEnv(unittest.TestCase):
    def test_run_success(self):
        old_aws_state = AwsState(
            aws_app_name='api',
            envs={
                EnvType.DEV: {
                    AwsTierType.WEB:
                    AwsTier(
                        tier_type=AwsTierType.WEB,
                        platform_arn='Test ARN',
                        parsed_version=ParsedVersion(
                            app='api',
                            circleci_build_num=123,
                            clean_branch_name='unit_test',
                            git_commit='5fcc3edf43a0adf59efb74f84dc2fbc455bedc74',
                            version_string='api-unit_test-123-5fcc3edf43a0adf59efb74f84dc2fbc455bedc74',
                        ),
                        environment_id='98765',
                        name='unit-test-env-021',
                        num=21,
                    )
                }
            },
        )
        new_aws_state = AwsState(
            aws_app_name='api',
            envs={
                EnvType.DEV: {
                    AwsTierType.WEB:
                    AwsTier(
                        tier_type=AwsTierType.WEB,
                        platform_arn='Test ARN',
                        parsed_version=ParsedVersion(
                            app='api',
                            circleci_build_num=125,
                            clean_branch_name='unit_test',
                            git_commit='6b69384109c6f3348ccaf4d5e761808f710bd6a9',
                            version_string='api-unit_test-125-6b69384109c6f3348ccaf4d5e761808f710bd6a9',
                        ),
                        environment_id=None,
                        name='unit-test-env-021',
                        num=21,
                    )
                }
            },
        )
        eb_client = MagicMock()
        eb_client.describe_environment_health = MagicMock(return_value={'HealthStatus': 'Ok'})
        result_logger = ResultLogger(log_git=False)
        SameEnv(EnvType.DEV, old_aws_state, new_aws_state, eb_client, result_logger, update_wait=1).run()
