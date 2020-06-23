#!/usr/bin/env python3

# Currently for deploying when you also want to create a new
# environment, not for redeploying to an existing environment.

import sys
if sys.version_info.major < 3 or sys.version_info.minor < 7:
    print("Error: This script requires at least Python 3.7.", file=sys.stderr)
    exit(1)

import argparse
import boto3
import pprint
import re
import safecast_deploy
import safecast_deploy.new_env
import safecast_deploy.same_env
import safecast_deploy.ssh
import safecast_deploy.state
import time


def parse_args():
    p = argparse.ArgumentParser()
    ps = p.add_subparsers()

    list_arns_p = ps.add_parser('list_arns', help="List all currently recommended Ruby ARNS.")
    list_arns_p.set_defaults(func=run_list_arns)

    desc_template_p = ps.add_parser('desc_template', help="Show a saved template's configuration.")
    desc_template_p.add_argument('app',
                                 choices=['api', 'ingest'],
                                 help="The application this template belongs to.",)
    desc_template_p.add_argument('template', help="The template's name.",)
    desc_template_p.set_defaults(func=run_desc_template)

    new_env_p = ps.add_parser('new_env', help="Create and switch to a completely new environment.")
    new_env_p.add_argument('app',
                           choices=['api', 'ingest'],
                           help="The target application to deploy to.",)
    new_env_p.add_argument('env',
                           choices=['dev', 'prd'],
                           help="The target environment to deploy to.",)
    new_env_p.add_argument('version', help="The new version to deploy.")
    new_env_p.add_argument('arn', help="The ARN the new deployment should use.")
    new_env_p.set_defaults(func=run_new_env)

    same_env_p = ps.add_parser('same_env', help='Deploy a new version of the app to the existing environment.')
    same_env_p.add_argument('app',
                            choices=['api', 'ingest'],
                            help="The target application to deploy to.",)
    same_env_p.add_argument('env',
                            choices=['dev', 'prd'],
                            help="The target environment to deploy to.",)
    same_env_p.add_argument('version', help="The new version to deploy.")
    same_env_p.set_defaults(func=run_same_env)

    ssh_p = ps.add_parser('ssh', help='SSH to the selected environment.')
    ssh_p.add_argument('app',
                       choices=['api', 'ingest', ],
                       help="The target application.",)
    ssh_p.add_argument('env',
                       choices=['dev', 'prd', ],
                       help="The target environment.",)
    ssh_p.add_argument('role',
                       choices=['web', 'wrk', ],
                       help="The type of server.",)
    ssh_p.add_argument('-s', '--select', action='store_true',
                       help="Select the specific server from a list. Otherwise, will connect to the first server found.",)
    ssh_p.set_defaults(func=run_ssh)

    versions_p = ps.add_parser('versions', help='List the deployable versions for this environment, sorted by age.')
    versions_p.add_argument('app',
                            choices=['api', 'ingest', ],
                            help="The target application.",)
    versions_p.set_defaults(func=run_versions)

    args = p.parse_args()
    args.func(args)


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


def run_desc_template(args):
    c = boto3.client('elasticbeanstalk')
    template = c.describe_configuration_settings(
        ApplicationName=args.app,
        TemplateName=args.template,
    )
    pprint.PrettyPrinter(stream=sys.stderr).pprint(template)


def run_new_env(args):
    state = safecast_deploy.state.State(args.app,
                                  args.env,
                                  new_version=args.version,
                                  new_arn=args.arn)
    safecast_deploy.new_env.NewEnv(state).run()


def run_same_env(args):
    state = safecast_deploy.state.State(args.app,
                                  args.env,
                                  new_version=args.version,)
    safecast_deploy.same_env.SameEnv(state).run()


def run_ssh(args):
    state = safecast_deploy.state.State(args.app, args.env)
    safecast_deploy.ssh.Ssh(state, args).run()


def run_versions(args):
    state = safecast_deploy.state.State(args.app)
    print(*state.available_versions, sep='\n')


def main():
    parse_args()
    # TODO update Grafana panels
    #
    # TODO method to switch to maintenance page
    #
    # TODO method to clean out old versions


if __name__ == '__main__':
    main()
