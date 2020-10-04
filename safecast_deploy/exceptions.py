class InvalidVersionException(Exception):
    def __init__(self, message, version):
        self.message = message
        self.version = version


class InvalidEnvStateException(Exception):
    def __init__(self, message, env_type, tier_type):
        self.message = message
        self.env_type = env_type
        self.tier_type = tier_type


class EnvNotHealthyException(Exception):
    def __init__(self, message, env_name, health):
        self.message = message
        self.env_name = env_name
        self.health = health


class EnvUpdateTimedOutException(Exception):
    def __init__(self, message, env_name, timeout_length):
        self.message = message
        self.env_name = env_name
        self.health = health
