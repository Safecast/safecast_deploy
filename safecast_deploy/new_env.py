import datetime
import pprint
import sys

from safecast_deploy import verbose_sleep
from safecast_deploy.aws_state import AwsTierType
from safecast_deploy.exceptions import EnvUpdateTimedOutException


class NewEnv:
    def __init__(self, target_env_type, old_aws_state, new_aws_state, eb_client, result_logger,
                 config_saver, update_templates, update_wait=70, total_update_wait=480):
        self._target_env_type = target_env_type
        self._aws_app_name = old_aws_state.aws_app_name
        self._old_aws_env_state = old_aws_state.envs[target_env_type]
        self._new_aws_env_state = new_aws_state.envs[target_env_type]
        self._c = eb_client
        self._result_logger = result_logger
        self._config_saver = config_saver
        self._update_templates = update_templates
        self._update_wait = update_wait
        self._total_update_wait = total_update_wait

    def run(self):
        self._start_time = datetime.datetime.now(datetime.timezone.utc)
        if self._update_templates:
            self._config_saver.run()

        # Handle the worker tier first, to ensure that database
        # migrations are applied
        if AwsTierType.WORKER in self._old_aws_env_state:
            self._handle_tier(self._old_aws_env_state[AwsTierType.WORKER], self._new_aws_env_state[AwsTierType.WORKER])
        self._handle_tier(self._old_aws_env_state[AwsTierType.WEB], self._new_aws_env_state[AwsTierType.WEB])

        result = self._generate_result()
        self._result_logger.log_result(result)

    def _handle_tier(self, old_tier, new_tier):
        template_name = f'{self._target_env_type}' if old_tier.tier_type is AwsTierType.WEB else f'{self._target_env_type}-{old_tier.tier_type}'

        if old_tier.tier_type is AwsTierType.WORKER:
            print("Setting the worker tier to scale to 0, in order to stop it and avoid concurrent processing problems.", file=sys.stderr)
            self._stop_tier(self._aws_app_name, old_tier.name)

        print(f"Creating the new environment {new_tier.name}.", file=sys.stderr)
        self._c.create_environment(
            ApplicationName=self._aws_app_name,
            EnvironmentName=new_tier.name,
            PlatformArn=new_tier.platform_arn,
            TemplateName=template_name,
            VersionLabel=new_tier.parsed_version.version_string,
        )
        self._wait_for_green(new_tier.name)

        if new_tier.tier_type is AwsTierType.WEB:
            print("Swapping web environment CNAMEs.", file=sys.stderr)
            self._c.swap_environment_cnames(
                SourceEnvironmentName=old_tier.name,
                DestinationEnvironmentName=new_tier.name,
            )

        verbose_sleep(self._update_wait)
        print(f"Terminating the old environment {old_tier.name}.", file=sys.stderr)
        self._c.terminate_environment(EnvironmentName=old_tier.name)

    def _stop_tier(self, app_name, tier_name):
        self._c.update_environment(
            ApplicationName=app_name,
            EnvironmentName=tier_name,
            OptionSettings=[
                {
                    'ResourceName': 'AWSEBAutoScalingGroup',
                    'Namespace': 'aws:autoscaling:asg',
                    'OptionName': 'MaxSize',
                    'Value': '0',
                },
                {
                    'ResourceName': 'AWSEBAutoScalingGroup',
                    'Namespace': 'aws:autoscaling:asg',
                    'OptionName': 'MinSize',
                    'Value': '0'
                },
            ],
        )
        verbose_sleep(480)

    def _generate_result(self):
        completed_time = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'app': self._aws_app_name,
            'completed_at': completed_time,
            'elapsed_time': (completed_time - self._start_time).total_seconds(),
            'env': self._target_env_type.value,
            'event': 'new_env',
            'started_at': self._start_time,
        }
        for new_tier_type, new_tier in self._new_aws_env_state.items():
            old_tier = self._old_aws_env_state[new_tier_type]
            result.update(
                {
                    f'{new_tier_type.value}': {
                        'new_env': new_tier.name,
                        'new_version_parsed': new_tier.parsed_version.to_dict(),
                        'old_env': old_tier.name,
                        'old_version_parsed': old_tier.parsed_version.to_dict(),
                    }
                }
            )
            self._add_git(new_tier_type, old_tier, new_tier, result)
        return result

    def _add_git(self, new_tier_type, old_tier, new_tier, result):
        # TODO move this out into a config file
        repo_names = {
            'api': 'safecastapi',
            'ingest': 'ingest',
            'reporting': 'reporting',
        }
        if (old_tier.parsed_version.git_commit is not None) \
           and (new_tier.parsed_version.git_commit is not None):
            result[new_tier_type.value]['github_diff'] = 'https://github.com/Safecast/{}/compare/{}...{}'.format(
                repo_names[self._aws_app_name],
                old_tier.parsed_version.git_commit,
                new_tier.parsed_version.git_commit,
            )

    def _wait_for_green(self, env_name):
        print(
            f"Waiting for {env_name} health to return to normal. Waiting {self._update_wait} seconds before first check to ensure an accurate starting point.",
            file=sys.stderr
        )
        verbose_sleep(self._update_wait)
        wait_seconds = 0
        while wait_seconds < self._total_update_wait:
            health = self._c.describe_environment_health(
                EnvironmentName=env_name,
                AttributeNames=['HealthStatus', ]
            )['HealthStatus']
            if health == 'Ok':
                print(f"{env_name} health has returned to normal.", file=sys.stderr)
                return
            verbose_sleep(self._update_wait)
            wait_seconds += self._update_wait
        raise EnvUpdateTimedOutException(
            "f{env_name} health did not return to normal within f{self._total_update_wait} seconds.",
            env_name, self._total_update_wait
        )
