from enum import Enum, unique

@unique
class EnvType(str, Enum):
    DEV = 'dev'
    PROD = 'prd'

    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)
