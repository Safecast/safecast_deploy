import boto3
import datetime
import pprint
import sys

from safecast_deploy import verbose_sleep
from safecast_deploy.aws_state import AwsTierType, EnvType
from safecast_deploy.result_logger import ResultLogger
from safecast_deploy.state import State


def run_cli(args):
    app = args.app
    env = EnvType(args.env) if args.env else None
    tier = AwsTierType(args.tier) if args.tier else None
    ConfigSaver(boto3.client('elasticbeanstalk'), ResultLogger()).run(app=app, env=env, tier=tier)


class ConfigSaver:
    # This class is not thread-safe.
    def __init__(self, eb_client, result_logger):
        self._c = eb_client
        self._result_logger = result_logger
        self._completed_list = []

    def run(self, app=None, env=None, tier=None):
        all_apps = ['api', 'ingest', 'recording']
        states = {}
        if app is None:
            for default_app in all_apps:
                states[default_app] = State(default_app, self._c).old_aws_state
        else:
            states[app] = State(app, self._c).old_aws_state

        for state in states:
            self.process_state(states[state], env, tier)
        self._result_logger.log_result(self._completed_list)
        self._completed_list = []

    def process_state(self, state, env, tier):
        if env is None:
            for available_env in state.envs:
                self.process_env(state, available_env, tier)
        else:
            self.process_env(state, env, tier)

    def process_env(self, state, env, tier):
        template_names = {
            AwsTierType.WEB: env.value,
            AwsTierType.WORKER: f'{env.value}-wrk',
        }
        if tier is None:
            for available_tier in state.envs[env]:
                self.process_tier(state, env, available_tier, template_names)
        else:
            self.process_tier(state, env, tier, template_names)

    def process_tier(self, state, env, tier, template_names):
        start_time = datetime.datetime.now(datetime.timezone.utc)
        template_name = template_names[tier]
        app = state.aws_app_name
        env_id = state.envs[env][tier].environment_id
        env_name = state.envs[env][tier].name
        print(f"Starting update of template {template_name} from {env_name}", file=sys.stderr)
        self._c.delete_configuration_template(
            ApplicationName=app,
            TemplateName=template_name,
        )
        verbose_sleep(5)
        self._c.create_configuration_template(
            ApplicationName=app,
            TemplateName=template_name,
            EnvironmentId=env_id,
        )
        print(f"Completed update of template {template_name} from {env_name}", file=sys.stderr)
        completed_time = datetime.datetime.now(datetime.timezone.utc)
        self._completed_list.append({
            'app': app,
            'completed_at': completed_time,
            'elapsed_time': (completed_time - start_time).total_seconds(),
            'env': env,
            'event': 'save_configs',
            'tier': tier,
            'source_env_id': env_id,
            'source_env_name': env_name,
            'started_at': start_time,
            'template_name': template_name,
        })
