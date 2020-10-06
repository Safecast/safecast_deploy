from dataclasses import dataclass
from dataclasses_json import dataclass_json
from enum import Enum, unique


@unique
class EnvType(str, Enum):
    """Encodes Safecast's understanding of environment types.
    """
    DEV = 'dev'
    PROD = 'prd'

    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)


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
    envs: dict  # dictionary mapping EnvTypes to a nested dictionary of AwsTierTypes to AwsTier objects


@dataclass_json
@dataclass(frozen=True)
class AwsTier:
    tier_type: AwsTierType
    platform_arn: str
    parsed_version: ParsedVersion
    name: str
    num: int
