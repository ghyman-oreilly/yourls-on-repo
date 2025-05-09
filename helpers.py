import os


class EnvMissingError(Exception):
    """Raised when a required environment variable is missing."""
    pass


def get_and_validate_env(env_name: str):
    env = os.getenv(env_name)

    if not env:
        raise EnvMissingError(f"Required env variable {env_name} not found.")
    
    return env
