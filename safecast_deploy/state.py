import boto3
import collections
import dataclasses
import re
import sys

from safecast_deploy import aws_state
from safecast_deploy.aws_state import AwsState, AwsTier, ParsedVersion, EnvType, AwsTierType
from safecast_deploy.exceptions import InvalidVersionException
from functools import lru_cache


class State:
    def __init__(self, aws_app_name, eb_client):
        self.aws_app_name = aws_app_name
        self._c = eb_client

        self._classify_available_versions()

        self.old_aws_state = AwsState(
            aws_app_name=self.aws_app_name,
            envs=self._build_envs(),
        )

    @lru_cache(typed=True)
    def new_aws_state(self, target_env_type, new_version=None, new_arn=None):
        self._validate_version(new_version)
        parsed_version = self._parse_version(new_version)
        new_envs = collections.defaultdict(dict)
        new_env_num = max([(tier.num + 1) % 1000 for (tier_type, tier) in self.old_aws_state.envs[target_env_type]], key=operator.itemgetter(1))
        for (tier_type, tier) in self.old_aws_state.envs[target_env_type]:
            new_tier = dataclasses.replace(tier)
            if new_version is not None:
                new_tier = dataclasses.replace(new_tier, version=new_version, parsed_version=parsed_version)
            if new_arn is not None:
                # A new ARN implies a new environment
                new_tier = dataclasses.replace(
                    new_tier,
                    platform_arn=new_arn,
                    environment_id=None,
                    name=f'safecast{self.old_aws_state.aws_app_name}-{target_env_type.value}-'
                    '{AwsTierType.WORKER.value + '-' if tier_type is AwsTierType.WORKER else ''}{new_env_num:03}',
                    num=new_env_num
                )
            new_envs[target_env_type][tier_type] = new_tier
        return dataclasses.replace(self.old_aws_state, envs=envs)

    def _validate_version(self, version):
        if version is None:
            return
        if version in self.failed_versions:
            raise InvalidVersionException("Version is marked as 'failed' at AWS and cannot be deployed.", version)
        if version not in self.available_versions:
            raise InvalidVersionException("Version was not found at AWS.", version)
        return

    def _parse_version(self, version_str):
        if version_str is None:
            return None

        git_hash_pattern = re.compile(r'^(?P<app>(api|ingest|reporting))-(?P<clean_branch_name>.+)-(?P<build_num>\d+)-(?P<commit>[0-9a-f]{40})$')
        no_git_hash_pattern = re.compile(r'^(?P<app>(api|ingest|reporting))-(?P<clean_branch_name>.+)-(?P<build_num>\d+)$')
        git_match = git_hash_pattern.match(version_str)
        no_git_match = no_git_hash_pattern.match(version_str)
        git_commit = None
        if git_match:
            match = git_match
            git_commit = match.group('commit')
        elif no_git_match:
            match = no_git_match
            # TODO: var is undefined if an `eb deploy` bundle is in use, would be good have a fallback for that case
        return ParsedVersion(
            app=match.group('app'),
            circleci_build_num=int(match.group('build_num')),
            clean_branch_name=match.group('clean_branch_name'),
            git_commit=git_commit,
            version_string=version_str,
        )

    def _build_envs(self):
        api_envs = self._c.describe_environments(
            ApplicationName=self.aws_app_name,
            IncludeDeleted=False,
        )['Environments']
        name_pattern = re.compile('safecast' + self.aws_app_name + r'-(?P<env>(dev|dev-wrk|prd|prd-wrk))-(?P<num>\d{3})')
        envs = collections.defaultdict(dict)
        for api_env in api_envs:
            match = name_pattern.fullmatch(api_env['EnvironmentName'])
            if match is None:
                print(f"WARN: unrecognized environment {api_env['EnvironmentName']}, not processing", file=sys.stderr)
                continue
            env_str = match.group('env')
            tier_type = AwsTierType.WEB
            if env_str.endswith('-wrk'):
                tier_type = AwsTierType.WORKER
                env_str = env_str[:-4]
            env_type = EnvType(env_str)
            tier = AwsTier(
                tier_type=tier_type,
                platform_arn=api_env['PlatformArn'],
                parsed_version=self._parse_version(api_env['VersionLabel']),
                environment_id=api_env['EnvironmentId'],
                name=api_env['EnvironmentName'],
                num=int(match.group('num')),
            )
            if (env_type in envs) and (tier_type in envs[env_type]):
                raise InvalidEnvStateException(
                    f"More than one {tier_type} tier in {env_type} environment was found, which one is the current environment?",
                    env_type, tier_type
                )
            envs[env_type][tier_type] = tier
        return envs

    def _classify_available_versions(self):
        self.api_versions = sorted(
            self._c.describe_application_versions(
                ApplicationName=self.aws_app_name
            )['ApplicationVersions'],
            key=lambda i: i['DateUpdated'],
        )
        self.available_versions = [o['VersionLabel'] for o in self.api_versions
                                   if o['Status'] != 'FAILED']
        self.failed_versions = [o['VersionLabel'] for o in self.api_versions
                                if o['Status'] == 'FAILED']
