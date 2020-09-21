class InvalidVersionException(Exception):
    def __init__(self, message, version):
        self.message = message
        self.version = version

class InvalidEnvStateException(Exception):
    def __init__(self, message, env_type, tier_type):
        self.message = message
        self.env_type = env_type
        self.tier_type = tier_type
