import datetime
import pprint
import sys

from safecast_deploy import config_saver, git_logger, verbose_sleep


class NewEnv:
    def __init__(self, state, update_templates):
        self.state = state
        self._c = state.eb_client
        self.update_templates = update_templates

    def run(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        if self.update_templates:
            config_saver.ConfigSaver(
                app=self.state.app, env=self.state.env
            ).run()
        # Handle the worker environment first, to ensure that database
        # migrations are applied
        self._calculate_new_envs()
        if self.state.has_worker:
            self._handle_worker()
        self._handle_web()
        result = self._generate_result()
        self._print_result(result)
        git_logger.log_result(result)

    def _handle_worker(self):
        # First, turn off the current worker to avoid any concurrency issues
        print("Setting the worker tier to scale to 0.", file=sys.stderr)
        self._c.update_environment(
            ApplicationName=self.state.app,
            EnvironmentName=self.state.env_metadata[self.state.subenvs['wrk']]['name'],
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
            ])
        verbose_sleep(480)
        print("Creating the new worker environment.", file=sys.stderr)
        self._c.create_environment(
            ApplicationName=self.state.app,
            EnvironmentName=self.new_env_metadata['wrk']['name'],
            PlatformArn=self.state.new_arn,
            TemplateName=self.state.subenvs['wrk'],
            VersionLabel=self.state.new_version,
        )
        self._wait_for_green(self.new_env_metadata['wrk']['name'])
        print("Terminating the old worker environment.", file=sys.stderr)
        self._c.terminate_environment(EnvironmentName=self.state.env_metadata[self.state.subenvs['wrk']]['name'])

    def _handle_web(self):
        print("Creating the new Web environment.", file=sys.stderr)
        self._c.create_environment(
            ApplicationName=self.state.app,
            EnvironmentName=self.new_env_metadata['web']['name'],
            PlatformArn=self.state.new_arn,
            TemplateName=self.state.subenvs['web'],
            VersionLabel=self.state.new_version,
        )
        self._wait_for_green(self.new_env_metadata['web']['name'])
        print("Swapping web environment CNAMEs.", file=sys.stderr)
        self._c.swap_environment_cnames(
            SourceEnvironmentName=self.state.env_metadata[self.state.subenvs['web']]['name'],
            DestinationEnvironmentName=self.new_env_metadata['web']['name'],
        )
        verbose_sleep(120)
        print("Terminating the old web environment.", file=sys.stderr)
        self._c.terminate_environment(EnvironmentName=self.state.env_metadata[self.state.subenvs['web']]['name'])

    def _generate_result(self):
        completed_time = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'app': self.state.app,
            'completed_at': completed_time,
            'elapsed_time': (completed_time - self.start_time).total_seconds(),
            'env': self.state.env,
            'event': 'new_env',
            'started_at': self.start_time,
            'web': {
                'new_env': self.new_env_metadata['web']['name'],
                'new_version': self.state.new_version,
                'new_version_parsed': self.state.new_versions_parsed['web'],
                'old_env': self.state.env_metadata[self.state.subenvs['web']]['name'],
                'old_version': self.state.env_metadata[self.state.subenvs['web']]['version'],
                'old_version_parsed': self.state.old_versions_parsed['web'],
            },

        }
        self._add_git('web', result)

        if self.state.has_worker:
            result['wrk'] = {
                'env': self.state.env_metadata[self.state.subenvs['wrk']]['name'],
                'new_version': self.state.new_version,
                'new_version_parsed': self.state.new_versions_parsed['wrk'],
                'old_version': self.state.env_metadata[self.state.subenvs['wrk']]['version'],
                'old_version_parsed': self.state.old_versions_parsed['wrk'],
            }
            self._add_git('wrk', result)

        return result

    def _add_git(self, tier, result):
        repo_names = {
            'api': 'safecastapi',
            'ingest': 'ingest',
            'reporting': 'reporting',
        }
        if 'git_commit' in self.state.old_versions_parsed[tier] \
           and 'git_commit' in self.state.new_versions_parsed[tier]:
            result[tier]['github_diff'] = 'https://github.com/Safecast/{}/compare/{}...{}'.format(
                repo_names[self.state.app],
                self.state.old_versions_parsed[tier]['git_commit'],
                self.state.new_versions_parsed[tier]['git_commit']
            )

    def _print_result(self, result):
        pprint.PrettyPrinter(stream=sys.stderr).pprint(result)
        print("Deployment completed.", file=sys.stderr)

    def _calculate_new_envs(self):
        new_num = self._balance_env_num()
        self.new_env_metadata = {
            'web': {
                'name': 'safecast{app}-{env}-{num:03}'.format(
                    app=self.state.app,
                    env=self.state.env,
                    num=new_num
                )
            },
            'wrk': {
                'name': 'safecast{app}-{env}-wrk-{num:03}'.format(
                    app=self.state.app,
                    env=self.state.env,
                    num=new_num
                )
            },
        }

    def _balance_env_num(self):
        web_num = (self.state.env_metadata[self.state.subenvs['web']]['num'] + 1) % 1000
        if self.state.has_worker:
            wrk_num = (self.state.env_metadata[self.state.subenvs['wrk']]['num'] + 1) % 1000
            return max(web_num, wrk_num)
        else:
            return web_num

    def _wait_for_green(self, env_name):
        verbose_sleep(70)
        wait_seconds = 0
        while wait_seconds < 540:
            health = self._c.describe_environment_health(
                EnvironmentName=env_name,
                AttributeNames=['HealthStatus', ]
            )['HealthStatus']
            if health == 'Ok':
                print("Environment health has returned to normal.", file=sys.stderr)
                return
            verbose_sleep(40)
            wait_seconds += 40
        print("Environment health did not return to normal within 540 seconds. Aborting further operations.",
              file=sys.stderr)
        exit(1)
