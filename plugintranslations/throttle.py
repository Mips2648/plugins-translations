import time
from functools import wraps

class Throttle(object):
    """
    Decorator that prevents a function from being called more than once every time period,
    and retries with exponential backoff on TooManyRequestsException.
    """

    def __init__(self, seconds: float = 0.1, max_retries: int = 5, backoff_base: float = 10):
        time.monotonic()
        self.throttle_period = seconds
        self.time_of_last_call = 0.0
        self.max_retries = max_retries
        self.backoff_base = backoff_base

    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            import deepl
            now = time.monotonic()
            time_since_last_call = now - self.time_of_last_call

            if time_since_last_call > self.throttle_period:
                self.time_of_last_call = now
            else:
                wait_seconds = self.throttle_period - time_since_last_call
                time.sleep(wait_seconds)
                self.time_of_last_call = time.monotonic()

            last_exception = None
            for attempt in range(self.max_retries):
                try:
                    return fn(*args, **kwargs)
                except deepl.exceptions.TooManyRequestsException as e:
                    last_exception = e
                    # Exponential backoff
                    delay = self.backoff_base * (2 ** attempt)
                    print(f"[Throttle] Too many requests, retrying in {delay}s (attempt {attempt+1}/{self.max_retries})")
                    time.sleep(delay)
            # Si on a échoué après tous les essais, on relance la dernière exception
            raise last_exception

        return wrapper
