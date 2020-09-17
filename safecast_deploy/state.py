import boto3
import re
import sys

from aws_state import AwsState, AwsTier, ParsedVersion, AwsTierType
from env_type import EnvType

class State:
    def __init__(
            self,
            aws_app_name,
            eb_client,
            new_version=None,
            new_arn=None):
        self.aws_app_name = aws_app_name
        self.new_version = new_version
        self.new_arn = new_arn
        self._c = eb_client

        self.subenvs = {
            'web': env,
            'wrk': '{}-wrk'.format(env),
        }

        self._identify_current_envs()
        self._classify_available_versions()
        self._validate_version()

    def old_aws_state(self):
        return AwsState(
            aws_app_name=self.aws_app_name,
            envs=self._build_envs(),
        )

    def new_aws_state(self):
        return old_aws_state.copy()#necessary changes

    def _validate_version(self):
        if self.new_version is None:
            return
        if self.new_version in self.failed_versions:
            print("ERROR: New version is marked as 'failed' at AWS and cannot be deployed.", file=sys.stderr)
            exit(1)
        if self.new_version not in self.available_versions:
            print("ERROR: New version was not found at AWS.", file=sys.stderr)
            exit(1)
        self.old_versions_parsed = {
            'web': self._parse_version(self.env_metadata[self.subenvs['web']]['version'])
        }
        self.new_versions_parsed = {
            'web': self._parse_version(self.new_version)
        }
        if self.has_worker:
            self.old_versions_parsed['wrk'] = self._parse_version(self.env_metadata[self.subenvs['wrk']]['version'])
            self.new_versions_parsed['wrk'] = self._parse_version(self.new_version)

    def _parse_version(self, version_str):
        if version_str is None:
            return
        git_hash_pattern = re.compile(r'^(?P<app>(api|ingest|reporting))-(?P<clean_branch_name>.+)-(?P<build_num>\d+)-(?P<commit>[0-9a-f]{40})$')
        no_git_hash_pattern = re.compile(r'^(?P<app>(api|ingest|reporting))-(?P<clean_branch_name>.+)-(?P<build_num>\d+)$')
        git_match = git_hash_pattern.match(version_str)
        no_git_match = no_git_hash_pattern.match(version_str)
        git_commit = None
        if git_match:
            match = git_match
            git_commit=match.group('commit')
        elif no_git_match:
            match = no_git_match
        # TODO: var is undefined if an `eb deploy` bundle is in use, would be good have a fallback for that case
        return ParsedVersion(
            app=match.group('app'),
            circleci_build_num=int(match.group('build_num')),
            clean_branch_name=match.group('clean_branch_name'),
            git_commit=git_commit
        )

    def _identify_current_envs(self):
        api_envs = self._c.describe_environments(
            ApplicationName=self.aws_app_name, IncludeDeleted=False)['Environments']
        name_pattern = re.compile('safecast' + self.aws_app_name + r'-(?P<env>(dev|dev-wrk|prd|prd-wrk))-(?P<num>\d{3})')
        self.env_metadata = {}
        for api_env in api_envs:
            match = name_pattern.fullmatch(api_env['EnvironmentName'])
            if match is None:
                print(f"WARN: unrecognized environment {api_env['EnvironmentName']}, not processing", file=sys.stderr)
                continue
            env_type = EnvType.fromString(match.group('env'))
            if env in self.env_metadata:
                print("More than one "
                      + env
                      + """ environment was found, which one is the current environment?\n
                      TODO implement this once it becomes a problem. Exiting.
                      """, file=sys.stderr)
                exit(1)
            self.env_metadata[match.group('env')] = {
                'api_env': api_env,
                'api_resources': self._c.describe_environment_resources(EnvironmentName=api_env['EnvironmentName'])['EnvironmentResources'],
                'name': api_env['EnvironmentName'],
                'num': int(match.group('num')),
                'version': api_env['VersionLabel'],
            }
        self.has_worker = self.subenvs['wrk'] in self.env_metadata

    def _classify_available_versions(self):
        self.api_versions = sorted(
            self._c.describe_application_versions(
                ApplicationName=self.app
            )['ApplicationVersions'],
            key=lambda i: i['DateUpdated'],
        )
        self.available_versions = [o['VersionLabel'] for o in self.api_versions
                                   if o['Status'] != 'FAILED']
        self.failed_versions = [o['VersionLabel'] for o in self.api_versions
                                if o['Status'] == 'FAILED']
