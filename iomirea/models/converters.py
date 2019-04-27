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
from errors import ConvertError, BadArgument, CheckError
from log import server_log


class _Default:
    def __repr__(self) -> str:
        return "<Empty default>"

    def __str__(self) -> str:
        return self.__repr__()


DEFAULT = _Default()

InputType = (
    typing.Any
)  # typing.Union[str, int, float, bool, typing.List[InputType], typing.Dict[str, InputType]]
OptionalInputType = typing.Optional[InputType]


class Converter:
    """Base converter."""

    ERROR_TEMPLATE = "Failed to convert parameter to {type}: {error.__class__.__name__}({error})"
    SUPPORTED_TYPES: typing.Tuple[typing.Any, ...] = (str, int, float, bool)

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
        """
        Used to convert value to converter type. Manages internal checks and
        should not be overriden.
        """

        if type(value) not in self.SUPPORTED_TYPES:
            raise BadArgument(
                self.error(
                    value, ValueError(f"Invalid input type: {type(value)}")
                )
            )

        try:
            result = await self._convert(value, app)
        except ConvertError:
            raise
        except ValueError as e:
            raise BadArgument(self.error(value, e))

        for check in self._checks:
            if not await check.check(result, app):
                raise CheckError(check.error(result))

        return result

    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> typing.Any:
        """Actual convert function that should be overriden."""

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


async def convert_map(
    converters: typing.Dict[str, Converter],
    query: typing.Mapping[str, InputType],
    app: aiohttp.web.Application,
    location: str = "body",
) -> typing.Dict[str, typing.Any]:
    """
    Converts mapping of elements generating new map with the same keys.
    Supports recursive maps/lists conversion.

    Propperly indicates problematic value in case of error with ConvertError.

    Known issues:
        Allows type implicit type casts, e.g: 1 can be treated as string
    """

    result = {}

    if not isinstance(query, typing.Mapping):
        raise ConvertError(f"Expected dict, got {type(query).__name__}", "")

    for name, converter in converters.items():
        if name not in query:
            try:
                # not converting default value to type, be careful
                result[name] = converter.get_default()
                continue
            except KeyError:  # no default value
                server_log.debug(f"Parameter {name}: missing")

                raise ConvertError(f"Missing from {location}", name)
        try:
            result[name] = await converter.convert(query[name], app)
        except ConvertError as e:
            e.update_parameter(name)

            if type(e) is BadArgument:
                server_log.debug(
                    f"Bad argument for parameter {e.parameter}: {e}"
                )

                raise ConvertError(
                    f"Should be of type {converter} in {location}", e.parameter
                )
            elif type(e) is CheckError:
                server_log.debug(f"Parameter {name}: check failed: {e}")

                raise ConvertError(
                    f"Check failed in {location}: {e}", e.parameter
                )
            else:
                raise ConvertError(str(e), e.parameter)

    return result


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


Snowflake = ID


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

        if type(value) is not str:
            return bool(value)

        lower_value = value.lower()

        if lower_value in self.POSITIVE:
            return True

        if lower_value in self.NEGATIVE:
            return False

        raise ValueError


class List(Converter):
    """
    Converter for list of elements. Enforces all items to be of the same type.
    Does not support map as container yet.
    """

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


class Map(Converter):
    SUPPORTED_TYPES = (dict,)

    def __init__(
        self, converters: typing.Dict[str, Converter], **kwargs: typing.Any
    ):
        super().__init__(**kwargs)

        self._converters = converters

    async def _convert(
        self, value: InputType, app: aiohttp.web.Application
    ) -> typing.Dict[str, typing.Any]:
        # TODO: json.loads for str type

        return await convert_map(self._converters, value, app)
