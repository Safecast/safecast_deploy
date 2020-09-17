import datetime
import pprint
import sys

from aws_state import AwsTierType
from safecast_deploy import git_logger, verbose_sleep


class SameEnv:
    def __init__(self, old_aws_state, new_aws_state, eb_client):
        self.old_aws_state = old_aws_state
        self.new_aws_state = new_aws_state
        self._c = eb_client

    def run(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

        # Handle the worker tier first, to ensure that database
        # migrations are applied
        self._update_environment(AwsTierType.WORKER)
        self._update_environment(AwsTierType.WEB)

        result = self._generate_result()
        self._print_result(result)
        git_logger.log_result(result)

    def _generate_result(self):
        completed_time = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'app': self.new_aws_state.aws_app_name,
            'completed_at': completed_time,
            'elapsed_time': (completed_time - self.start_time).total_seconds(),
            'env': self.new_aws_state.env_type.value,
            'event': 'same_env',
            'started_at': self.start_time,
        }
        for new_tier in self.new_aws_state.tiers:
            old_tier = self.old_aws_state.tiers[new_tier.tier]
            result.update(
                {
                    f'{new_tier.tier.value}': {
                        'env': new_tier.name,
                        'new_version': new_tier.version,
                        'new_version_parsed': dict(new_tier.parsed_version),
                        'old_version': old_tier.version,
                        'old_version_parsed': dict(old_tier.parsed_version),
                    },
                }
            )
            self._add_git(tier, result)

        return result

    def _add_git(self, role, result):
        repo_names = {
            'api': 'safecastapi',
            'ingest': 'ingest',
            'reporting': 'reporting',
        }
        if old_tier.parsed_version.git_commit is not None
           and new_tier.parsed_version.git_commit is not None:
            result[new_tier.tier.value]['github_diff'] = 'https://github.com/Safecast/{}/compare/{}...{}'.format(
                repo_names[self.old_aws_state.aws_app_name],
                old_tier.parsed_version.git_commit,
                new_tier.parsed_version.git_commit
            )

    def _print_result(self, result):
        pprint.PrettyPrinter(stream=sys.stderr).pprint(result)
        print("Deployment completed.", file=sys.stderr)

    def _update_environment(self, tier):
        if tier not in new_aws_state.tiers:
            return

        print(f"Deploying to the {tier.value} tier.", file=sys.stderr)
        env_name = self.new_aws_state.tiers[tier].name
        self._c.update_environment(
            ApplicationName=self.new_aws_state.aws_app_name,
            EnvironmentName=env_name,
            VersionLabel=self.new_aws_state.tiers[tier].version
        )

        self._wait_for_green(env_name)

    def _wait_for_green(self, env_name):
        print(f"Waiting for {env_name} health to return to normal.", file=sys.stderr)
        verbose_sleep(70)
        wait_seconds = 0
        while wait_seconds < 480:
            health = self._c.describe_environment_health(
                EnvironmentName=env_name,
                AttributeNames=['HealthStatus', ]
            )['HealthStatus']
            if health == 'Ok':
                print(f"{env_name} health has returned to normal.", file=sys.stderr)
                return
            verbose_sleep(40)
            wait_seconds += 40
        print("f{env_name} health did not return to normal within 480 seconds. Aborting further operations.",
              file=sys.stderr)
        exit(1)
