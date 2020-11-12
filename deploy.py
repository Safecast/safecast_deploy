#!/usr/bin/env python3

import sys
if sys.version_info.major < 3 or sys.version_info.minor < 8:
    print("Error: This script requires at least Python 3.8.", file=sys.stderr)
    exit(1)

import argcomplete
import argparse
import boto3
import json
import pprint
import re
import safecast_deploy
import safecast_deploy.config_saver
import safecast_deploy.grafana_updater
import safecast_deploy.new_env
import safecast_deploy.same_env
import safecast_deploy.ssh
import safecast_deploy.state
import time

from safecast_deploy.aws_state import AwsTierType, EnvType
from safecast_deploy.extended_json_encoder import ExtendedJSONEncoder
from safecast_deploy.result_logger import ResultLogger


def parse_args():
    p = argparse.ArgumentParser()
    ps = p.add_subparsers()

    list_arns_p = ps.add_parser('list_arns', help="List all currently recommended Ruby ARNS.")
    list_arns_p.set_defaults(func=run_list_arns)

    apps = ['api', 'ingest', 'reporting']
    environments = [type.value for type in list(EnvType)]
    tiers = [type.value for type in list(AwsTierType)]

    desc_metadata_p = ps.add_parser('desc_metadata', help="Describe the metadata available for this application.")
    desc_metadata_p.add_argument('app',
                                 choices=apps,
                                 help="The application to describe.",)
    desc_metadata_p.set_defaults(func=run_desc_metadata)

    desc_template_p = ps.add_parser('desc_template', help="Show a saved template's configuration.")
    desc_template_p.add_argument('app',
                                 choices=apps,
                                 help="The application this template belongs to.",)
    desc_template_p.add_argument('template', help="The template's name.",)
    desc_template_p.set_defaults(func=run_desc_template)

    new_env_p = ps.add_parser('new_env', help="Create and switch to a completely new environment.")
    new_env_p.add_argument('app',
                           choices=apps,
                           help="The target application to deploy to.",)
    new_env_p.add_argument('env',
                           choices=environments,
                           help="The target environment to deploy to.",)
    new_env_p.add_argument('version', help="The new version to deploy.")
    new_env_p.add_argument('arn', help="The ARN the new deployment should use.")
    new_env_p.add_argument(
        '--no-update-templates', action='store_true',
        help="If this flag is set, the script will not update the Elastic Beanstalk environment templates "
        + "from the currently running environments before beginning the deployment.",)
    new_env_p.set_defaults(func=run_new_env)

    same_env_p = ps.add_parser('same_env', help='Deploy a new version of the app to the existing environment.')
    same_env_p.add_argument('app',
                            choices=apps,
                            help="The target application to deploy to.",)
    same_env_p.add_argument('env',
                            choices=environments,
                            help="The target environment to deploy to.",)
    same_env_p.add_argument('version', help="The new version to deploy.")
    same_env_p.set_defaults(func=run_same_env)

    save_configs_p = ps.add_parser('save_configs',
                                   help="Overwrite the saved configuration templates from the current environments.")
    save_configs_p.add_argument('-a', '--app',
                                choices=apps,
                                help="Limit the overwrite to a specific application.")
    save_configs_p.add_argument('-e', '--env',
                                choices=environments,
                                help="Limit the overwrite to a specific environment.")
    save_configs_p.add_argument('-t', '--tier',
                                choices=tiers,
                                help="Limit the overwrite to a specific tier.")
    save_configs_p.set_defaults(func=safecast_deploy.config_saver.run_cli)

    ssh_p = ps.add_parser('ssh', help='SSH to the selected environment.')
    ssh_p.add_argument('app',
                       choices=apps,
                       help="The target application.",)
    ssh_p.add_argument('env',
                       choices=environments,
                       help="The target environment.",)
    ssh_p.add_argument('tier',
                       choices=tiers,
                       help="The type of server.",)
    ssh_p.add_argument('-s', '--select', action='store_true',
                       help="Choose a specific server. Otherwise, will connect to the first server found.",)
    ssh_p.set_defaults(func=run_ssh)

    update_grafana_p = ps.add_parser('update_grafana', help='Update the Grafana dashboard for the given application to match the running environment.')
    update_grafana_p.add_argument(
        'app',
        choices=apps,
        help="The target application.",)
    update_grafana_p.set_defaults(func=safecast_deploy.grafana_updater.run_cli)

    versions_p = ps.add_parser('versions', help='List the deployable versions for this environment, sorted by age.')
    versions_p.add_argument('app',
                            choices=apps,
                            help="The target application.",)
    versions_p.set_defaults(func=run_versions)

    argcomplete.autocomplete(p)
    args = p.parse_args()
    if 'func' in args:
        args.func(args)
    else:
        p.error("too few arguments")


def run_list_arns(args):
    c = boto3.client('elasticbeanstalk')
    platforms = c.list_platform_versions(
        Filters=[
            {
                'Type': 'ProgrammingLanguageName',
                'Operator': '=',
                'Values': ['Ruby', ],
            },
            {
                'Type': 'PlatformLifecycleState',
                'Operator': '=',
                'Values': ['recommended', ],
            },
        ]
    )['PlatformSummaryList']
    platform_arns = sorted([m['PlatformArn'] for m in platforms])
    print(*platform_arns, sep='\n')


def run_desc_metadata(args):
    state = safecast_deploy.state.State(args.app, boto3.client('elasticbeanstalk'))
    json.dump(state.old_aws_state.to_dict(), sys.stdout, sort_keys=True, indent=2)
    print()


def run_desc_template(args):
    c = boto3.client('elasticbeanstalk')
    template = c.describe_configuration_settings(
        ApplicationName=args.app,
        TemplateName=args.template,
    )
    json.dump(template, sys.stdout, sort_keys=True, indent=2, cls=ExtendedJSONEncoder)
    print()


def run_new_env(args):
    eb_client = boto3.client('elasticbeanstalk')
    result_logger = ResultLogger()
    state = safecast_deploy.state.State(args.app, eb_client)
    config_saver = safecast_deploy.config_saver.ConfigSaver(eb_client, result_logger)
    safecast_deploy.new_env.NewEnv(
        EnvType(args.env),
        state.old_aws_state,
        state.new_aws_state(new_version=args.version),
        boto3.client('elasticbeanstalk'),
        result_logger,
        config_saver,
        (not args.no_update_templates),
    ).run()


def run_same_env(args):
    state = safecast_deploy.state.State(args.app, boto3.client('elasticbeanstalk'))
    safecast_deploy.same_env.SameEnv(
        EnvType(args.env),
        state.old_aws_state,
        state.new_aws_state(new_version=args.version),
        boto3.client('elasticbeanstalk'),
        ResultLogger(),
    ).run()


def run_ssh(args):
    aws_state = safecast_deploy.state.State(args.app, boto3.client('elasticbeanstalk')).old_aws_state
    safecast_deploy.ssh.ssh(aws_state, EnvType(args.env), AwsTierType(args.tier), args.select)


def run_versions(args):
    state = safecast_deploy.state.State(args.app, boto3.client('elasticbeanstalk'))
    print(*state.available_versions, sep='\n')


def main():
    parse_args()
    # TODO method to switch to maintenance page


if __name__ == '__main__':
    main()
