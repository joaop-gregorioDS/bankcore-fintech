from common.metrics import meter

_meter = meter("bankcore.auth")

login_attempts = _meter.create_counter("bankcore_auth_login_attempts", unit="{attempt}")
login_results = _meter.create_counter("bankcore_auth_login_results", unit="{login}")
rate_limit_decisions = _meter.create_counter("bankcore_auth_rate_limit_decisions", unit="{decision}")
redis_failures = _meter.create_counter("bankcore_auth_redis_failures", unit="{failure}")
redis_recoveries = _meter.create_counter("bankcore_auth_redis_recoveries", unit="{recovery}")
