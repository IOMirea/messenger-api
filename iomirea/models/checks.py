"""
IOMirea-server - A server for IOMirea messenger
Copyright (C) 2019  Eugene Ershov

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""


from typing import Any, Callable, Awaitable, Optional, List

import aiohttp

from constants import BIGINT64_MAX_POSITIVE


class Check:
    ERROR_TEMPLATE = "Check {check} failed"

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        raise NotImplementedError

    def error(self, value: Any) -> str:
        return self.ERROR_TEMPLATE.format_map({"check": self, "value": value})

    def __str__(self) -> str:
        return self.__class__.__name__.lower()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"


class Between(Check):
    ERROR_TEMPLATE = (
        "Should be between {check.lower_bound} and {check.upper_bound}"
    )

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
    ERROR_TEMPLATE = "Should be less than {check.upper_bound}"

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
    ERROR_TEMPLATE = "Should be greater than {check.lower_bound}"

    def __init__(self, lower_bound: Any, inclusive: bool = True):
        self.lower_bound = lower_bound
        self.inclusive = inclusive

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return (
            value >= self.lower_bound
            if self.inclusive
            else value > self.lower_bound
        )


class LengthBetween(Between):
    ERROR_TEMPLATE = (
        "Length should be between {check.lower_bound} and {check.upper_bound}"
    )

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        value_len = len(value)

        left = (
            value_len >= self.lower_bound
            if self.inclusive_lower
            else value_len > self.lower_bound
        )
        right = (
            value_len <= self.upper_bound
            if self.inclusive_upper
            else value_len < self.upper_bound
        )

        return left and right


class Equals(Check):
    ERROR_TEMPLATE = "Should be equal to {check.other}"

    def __init__(self, other: Any):
        self.other = other

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return value == self.other


class OneOf(Check):
    ERROR_TEMPLATE = "Should be one of {check.allowed}"

    def __init__(self, allowed: List[Any]):
        self.allowed = allowed

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return value in self.allowed


class Custom(Check):
    def __init__(
        self,
        custom_fn: Callable[[Any, aiohttp.web.Application], Awaitable[bool]],
        error_template: str = Check.ERROR_TEMPLATE,
        name: Optional[str] = None,
    ):
        self.custom_fn = custom_fn
        self.ERROR_TEMPLATE = error_template
        self._name = name

    async def check(self, value: Any, app: aiohttp.web.Application) -> bool:
        return await self.custom_fn(value, app)

    def __str__(self) -> str:
        return super().__str__() if self._name is None else self._name
