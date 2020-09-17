from dataclasses import dataclass
from enum import Enum
from env_type import EnvType


@dataclass(frozen=True)
class AwsState:
    aws_app_name: str
    envs: Dict[EnvType, Dict[AwsTierType, AwsTier]]


@dataclass(frozen=True)
class AwsTier:
    tier: AwsTierType
    arn: str
    version: str
    name: str
    num: int
    parsed_version: ParsedVersion


@dataclass(frozen=True)
class ParsedVersion:
    app: str
    circle_ci_build_num: int
    clean_branch_name: str
    git_commit: str


class AwsTierType(Enum):
    WEB = 'web'
    WORKER = 'wrk'

    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)
