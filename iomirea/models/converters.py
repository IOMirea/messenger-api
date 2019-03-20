import math

from typing import Any, List

import aiohttp

from models import checks
from errors import ConvertError, CheckError


class Converter:
    error_template = (
        "Failed to convert parameter to {1}: {2.__class__.__name__}({2})"
    )

    def __init__(self, checks: List[checks.Check] = [], **kwargs: Any):
        if "default" in kwargs:
            self.default = kwargs["default"]

        self.checks = checks

    async def convert(self, value: str, app: aiohttp.web.Application) -> Any:
        try:
            result = await self._convert(value, app)
        except ConvertError:
            raise
        except Exception as e:
            raise ConvertError(self.error_template.format(value, self, e))

        for check in self.checks:
            if not await check.check(result, app):
                raise CheckError(check.error_template.format(result, check))

        return result

    async def _convert(self, value: str, app: aiohttp.web.Application) -> Any:
        raise NotImplementedError

    def __str__(self) -> str:
        return self.__class__.__name__.lower()


class Integer(Converter):
    async def _convert(self, value: str, app: aiohttp.web.Application) -> int:
        return int(value)


class ID(Integer):
    def __init__(self, **kwargs: Any):
        check = checks.BetweenXAndInt64(0)

        if "checks" not in kwargs:
            kwargs["checks"] = [check]
        else:
            kwargs["checks"].append(check)

        super().__init__(**kwargs)


class Number(Converter):
    async def _convert(
        self, value: str, app: aiohttp.web.Application
    ) -> float:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            raise ValueError

        return result


class String(Converter):
    async def _convert(self, value: str, app: aiohttp.web.Application) -> str:
        return value


class Boolean(Converter):
    POSITIVE = ["1", "y", "yes", "+", "positive"]
    NEGATIVE = ["0", "n", "no", "-", "negative"]

    async def _convert(self, value: str, app: aiohttp.web.Application) -> bool:
        lower_value = value.lower()

        if lower_value in self.POSITIVE:
            return True

        if lower_value in self.NEGATIVE:
            return False

        raise ValueError
