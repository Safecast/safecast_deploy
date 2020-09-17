from enum import Enum, unique


class EnvType(Enum):
    @unique
    DEV = 'dev'
    PROD = 'prd'

    reverse_map = {
        'dev': DEV,
        'prd': PROD,
        }
    
    @classmethod
    def fromString(cls, env):
        return reverse_map[env]

    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)
