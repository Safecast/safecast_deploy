import boto3
import datetime
import pprint
import sys

from safecast_deploy import state, verbose_sleep
from safecast_deploy.result_logger import ResultLogger


def run_cli(args):
    app = args.app
    env = EnvType(args.env) if args.env else None
    tier = AwsTierType(args.tier) if args.env else None
    ConfigSaver(boto3.client('elasticbeanstalk'), ResultLogger()).run(app=app, env=env, tier=tier)


class ConfigSaver:
    def __init__(self, eb_client, result_logger):
        self._c = eb_client
        self._result_logger = result_logger

    def run(self, app=None, env=None, tier=None):
        all_apps = ['api', 'ingest', 'recording']
        states = {}
        if app is None:
            for default_app in all_apps:
                states[default_app] = state.State(default_app, self._c)
        else:
            self.states[app] = state.State(app, self._c)

        completed_list = []
        for state in states:
            state_result = self.process_state(states[state].old_aws_state, env, tier)
            self._result_logger.log_result(state_result)

    def process_state(self, state, env, tier):
        if env is None:
            for default_env in list(EnvType):
                self.process_env(state, default_env, tier)
        else:
            self.process_env(state, env, tier)

    def process_env(self, state, env, tier):
        template_names = {
            AwsTierType.WEB: env.value,
            AwsTierType.WORKER: f'{env.value}-wrk',
        }
        if tier is None:
            for default_tier in list(AwsTierType):
                self.process_tier(state, env, default_tier, template_names)
        else:
            self.process_tier(state, env, tier, template_names)

    def process_tier(self, state, env, tier, template_names):
        start_time = datetime.datetime.now(datetime.timezone.utc)
        template_name = template_names[tier]
        env_id = state[env][tier].environment_id
        env_name = state[env][tier].name
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
        self.completed_list.append({
            'app': app,
            'completed_at': completed_time,
            'elapsed_time': (completed_time - start_time).total_seconds(),
            'env': env,
            'event': 'save_configs',
            'role': role,
            'source_env_id': env_id,
            'source_env_name': env_name,
            'started_at': start_time,
            'template_name': template_name,
        })
