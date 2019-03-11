from typing import Any, Callable, Awaitable

import aiohttp

from constants import BIGINT64_MAX_POSITIVE


class Check:
    error_template = "Check {2} failed"

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.__class__.__name__.lower()


class Between(Check):
    error_template = "Should be between {1.lower_bound} and {1.upper_bound}"

    def __init__(
        self,
        lower_bound: Any,
        upper_bound: Any,
        inclusive_lower: bool = True,
        inclusive_upper: bool = True,
    ):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.inclusive_lower = inclusive_lower
        self.inclusive_upper = inclusive_upper

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        left = (
            value >= self.lower_bound
            if self.inclusive_lower
            else value > self.lower_bound
        )
        right = (
            value <= self.upper_bound
            if self.inclusive_upper
            else value < self.upper_bound
        )

        return left and right


class BetweenXAndInt64(Between):
    def __init__(self, lower_bound: Any, inclusive: bool = True):
        super().__init__(
            lower_bound,
            BIGINT64_MAX_POSITIVE,
            inclusive_lower=inclusive,
            inclusive_upper=True,
        )

    def __str__(self) -> str:
        return super().__str__()


class Less(Check):
    error_template = "Should be less than {1.upper_bound}"

    def __init__(self, upper_bound: Any, inclusive: bool = True):
        self.upper_bound = upper_bound
        self.inclusive = inclusive

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return (
            value <= self.upper_bound
            if self.inclusive
            else value < self.upper_bound
        )


class Greater(Check):
    error_template = "Should be greater than {1.lower_bound}"

    def __init__(self, lower_bound: Any, inclusive: bool = True):
        self.lower_bound = lower_bound
        self.inclusive = inclusive

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return (
            value >= self.lower_bound
            if self.inclusive
            else value > self.lower_bound
        )


class Custom(Check):
    def __init__(
        self,
        custom_fn: Callable[[Any, aiohttp.web.Application], Awaitable[bool]],
    ):
        self.custom_fn = custom_fn

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return await self.custom_fn(value, app)
