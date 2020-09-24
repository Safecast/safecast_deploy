from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum, unique
from safecast_deploy import env_type


@unique
class AwsTierType(str, Enum):
    WEB = 'web'
    WORKER = 'wrk'

    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)


@dataclass_json
@dataclass(frozen=True)
class ParsedVersion:
    app: str
    circleci_build_num: int
    clean_branch_name: str
    git_commit: str
    version_string: str


@dataclass_json
@dataclass(frozen=True)
class AwsState:
    aws_app_name: str
    envs: dict


@dataclass_json
@dataclass(frozen=True)
class AwsTier:
    tier_type: AwsTierType
    platform_arn: str
    version: str
    parsed_version: ParsedVersion
    name: str
    num: int
