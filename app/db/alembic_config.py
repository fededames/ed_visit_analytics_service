def resolve_database_url(configured_url: str | None, settings_url: str, env_url: str | None) -> str:
    if configured_url and not configured_url.startswith("driver://"):
        return configured_url
    if env_url:
        return env_url
    return settings_url
