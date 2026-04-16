import time
import pytest
from plugintranslations.throttle import Throttle


class TestThrottle():

    def test_invalid_max_retries(self):
        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            Throttle(max_retries=0)

    def test_call(self):

        seconds_to_wait = 0.1
        max_calls = 10

        @Throttle(seconds=seconds_to_wait)
        def test_function():
            return "Function executed"
        start = time.monotonic()
        count = 0
        for _ in range(max_calls):
            result = test_function()
            count += 1
            if count < max_calls:
                # time.sleep(1.9)
                pass
            assert result == "Function executed"
        end = time.monotonic()
        elapsed = end - start
        assert elapsed >= seconds_to_wait * (max_calls - 1), f"Elapsed time {elapsed} should be at least {seconds_to_wait * (max_calls - 1)} seconds"
        assert count == max_calls, f"Function should be called {max_calls} times"
