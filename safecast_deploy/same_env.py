import datetime
import pprint
import sys

from safecast_deploy import git_logger, verbose_sleep


class SameEnv:
    def __init__(self, state):
        self.state = state
        self._c = state.eb_client

    def run(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)
        # Handle the worker environment first, to ensure that database
        # migrations are applied
        self._handle_worker()
        self._handle_web()
        result = self._generate_result()
        self._print_result(result)
        git_logger.log_result(result)

    def _handle_worker(self):
        if self.state.has_worker:
            print("Deploying to the worker.", file=sys.stderr)
            env_name = self.state.env_metadata[self.state.subenvs['wrk']]['name']
            self._update_environment(env_name)

    def _handle_web(self):
        print("Deploying to the web instances.", file=sys.stderr)
        env_name = self.state.env_metadata[self.state.subenvs['web']]['name']
        self._update_environment(env_name)

    def _generate_result(self):
        completed_time = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'app': self.state.app,
            'completed_at': completed_time,
            'elapsed_time': (completed_time - self.start_time).total_seconds(),
            'env': self.state.env,
            'event': 'same_env',
            'started_at': self.start_time,
            'web': {
                'env': self.state.env_metadata[self.state.subenvs['web']]['name'],
                'new_version': self.state.new_version,
                'new_version_parsed': self.state.new_versions_parsed['web'],
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

    def _add_git(self, role, result):
        repo_names = {
            'api': 'safecastapi',
            'ingest': 'ingest',
            'reporting': 'reporting',
        }
        if 'git_commit' in self.state.old_versions_parsed[role] \
           and 'git_commit' in self.state.new_versions_parsed[role]:
            result[role]['github_diff'] = 'https://github.com/Safecast/{}/compare/{}...{}'.format(
                repo_names[self.state.app],
                self.state.old_versions_parsed[role]['git_commit'],
                self.state.new_versions_parsed[role]['git_commit']
            )

    def _print_result(self, result):
        pprint.PrettyPrinter(stream=sys.stderr).pprint(result)
        print("Deployment completed.", file=sys.stderr)

    def _update_environment(self, env_name):
        self._c.update_environment(
            ApplicationName=self.state.app,
            EnvironmentName=env_name,
            VersionLabel=self.state.new_version,
        )
        print("Waiting for instance health to return to normal.", file=sys.stderr)
        self._wait_for_green(env_name)

    def _wait_for_green(self, env_name):
        verbose_sleep(70)
        wait_seconds = 0
        while wait_seconds < 480:
            health = self._c.describe_environment_health(
                EnvironmentName=env_name,
                AttributeNames=['HealthStatus', ]
            )['HealthStatus']
            if health == 'Ok':
                print("Environment health has returned to normal.", file=sys.stderr)
                return
            verbose_sleep(40)
            wait_seconds += 40
        print("Environment health did not return to normal within 480 seconds. Aborting further operations.",
              file=sys.stderr)
        exit(1)
