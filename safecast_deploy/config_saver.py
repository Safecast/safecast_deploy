import datetime
import pprint
import sys

from safecast_deploy import state, verbose_sleep


def run_cli(args):
    ConfigSaver(app=args.app, env=args.env, role=args.role).run()


class ConfigSaver:
    def __init__(self, result_logger, app=None, env=None, role=None):
        self.app = app
        self.env = env
        self.role = role
        self.states = {}
        if app is None:
            self.states['api'] = state.State('api')
            self.states['ingest'] = state.State('ingest')
            self.states['reporting'] = state.State('reporting')
            self._c = self.states['api'].eb_client
        else:
            self.states[app] = state.State(app)
            self._c = self.states[app].eb_client
        self.completed_list = []

    def run(self):
        for app in self.states:
            env_metadata = self.states[app].env_metadata
            if self.app is None:
                self.process_app('api')
                self.process_app('ingest')
            else:
                self.process_app(app)
        result_logger.log_result(self.completed_list)

    def process_app(self, app):
        if self.env is None:
            self.process_env(app, 'dev')
            self.process_env(app, 'prd')
        else:
            self.process_env(app, self.env)

    def process_env(self, app, env):
        template_names = {
            'web': env,
            'wrk': '{}-wrk'.format(env),
        }
        if self.role is None:
            self.process_role(app, env, 'web', template_names)
            if self.states[app].has_worker:
                self.process_role(app, env, 'wrk', template_names)
        else:
            self.process_role(app, env, self.role, template_names)

    def process_role(self, app, env, role, template_names):
        start_time = datetime.datetime.now(datetime.timezone.utc)
        template_name = template_names[role]
        env_id = self.states[app].env_metadata[template_name]['api_env']['EnvironmentId']
        env_name = self.states[app].env_metadata[template_name]['name']
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
            'source_env_name': env_name,
            'started_at': start_time,
            'template_name': template_name
        })
