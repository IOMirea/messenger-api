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


import math

import typing

import aiohttp

from models import checks
from errors import ConvertError, CheckError


class _Default:
    def __repr__(self) -> str:
        return "<Empty default>"

    def __str__(self) -> str:
        return self.__repr__()


DEFAULT = _Default()

InputType = (
    typing.Any
)  # typing.Union[str, int, float, typing.List[InputType], typing.Dict[str, InputType]]
OptionalInputType = typing.Optional[InputType]


class Converter:
    ERROR_TEMPLATE = "Failed to convert parameter to {type}: {error.__class__.__name__}({error})"
    SUPPORTED_TYPES: typing.Tuple[typing.Any, ...] = (str, int, float)

    def __init__(
        self,
        checks: typing.List[checks.Check] = [],
        default: typing.Any = DEFAULT,
        **kwargs: typing.Any,
    ):
        self._default = default
        self._checks = checks

    async def convert(
        self, value: OptionalInputType, app: aiohttp.web.Application
    ) -> typing.Any:
        if value is None:
            return None

        if type(value) not in self.SUPPORTED_TYPES:
            raise ConvertError(
                self.error(
                    value, ValueError(f"Invalid input type: {type(value)}")
                )
            )

        try:
            result = await self._convert(value, app)
        except ConvertError:
            raise
        except Exception as e:
            raise ConvertError(self.error(value, e))

        for check in self._checks:
            if not await check.check(result, app):
                raise CheckError(check.error(result))

        return result

    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> typing.Any:
        raise NotImplementedError

    @property
    def has_default(self) -> bool:
        return self._default is not DEFAULT

    def get_default(self) -> typing.Any:
        if not self.has_default:
            raise KeyError

        return self._default

    def error(self, value: typing.Any, e: Exception) -> str:
        return self.ERROR_TEMPLATE.format_map(
            {"value": value, "type": self, "error": e}
        )

    def __str__(self) -> str:
        return self.__class__.__name__.lower()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} checks={self._checks} default={self._default}>"


class Integer(Converter):
    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> int:
        return int(value)


class ID(Integer):
    def __init__(self, **kwargs: typing.Any):
        check = checks.BetweenXAndInt64(0)

        if "checks" not in kwargs:
            kwargs["checks"] = [check]
        else:
            kwargs["checks"].append(check)

        super().__init__(**kwargs)


class Number(Converter):
    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> float:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            raise ValueError

        return result


class String(Converter):
    def __init__(self, strip: bool = False, **kwargs: typing.Any):
        super().__init__(**kwargs)

        self.strip = strip

    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> str:
        value = str(value)

        return value.strip() if self.strip else value


class Boolean(Converter):
    POSITIVE = ["1", "y", "yes", "+", "positive"]
    NEGATIVE = ["0", "n", "no", "-", "negative"]

    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> bool:
        lower_value = value.lower()

        if lower_value in self.POSITIVE:
            return True

        if lower_value in self.NEGATIVE:
            return False

        raise ValueError


class List(Converter):
    SUPPORTED_TYPES = (str, list)

    def __init__(
        self, converter: Converter, max_len: int = -1, **kwargs: typing.Any
    ):
        super().__init__(**kwargs)

        self._converter = converter
        self._max_len = max_len

    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> typing.List[typing.Any]:
        results = []
        if self._max_len != -1 and len(value) > self._max_len:
            raise ConvertError("List converter: input is too long")

        for v in value:
            results.append(await self._converter.convert(v, app))

        return results

    def __str__(self) -> str:
        max_len_argument = f":{self._max_len}" if self._max_len != -1 else ""

        return f"{self.__class__.__name__.lower()}[{self._converter}{max_len_argument}]"
