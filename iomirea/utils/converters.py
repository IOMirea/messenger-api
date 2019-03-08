import math

from constants import BIGINT64_MAX_POSITIVE


# TODO: separate checks and converters?


class ConvertError(ValueError):
    pass


class CheckError(ValueError):
    pass


class Check:
    error_template = "Check {2} failed"

    @property
    def pretty_name(self):
        return self.__class__.__name__

    async def check(self, value, app):
        raise NotImplementedError

    def __str__(self):
        return self.pretty_name


class Between(Check):
    error_template = "Should be between {1.lower_bound} and {1.upper_bound}"

    def __init__(
        self, lower_bound, upper_bound, inclusive_lower=True, inclusive_upper=True
    ):
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.inclusive_lower = inclusive_lower
        self.inclusive_upper = inclusive_upper

    async def check(self, value, app):
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
    @property
    def pretty_name(self):
        return self.__bases__[0].pretty_name

    def __init__(self, lower_bound, inclusive=True):
        super().__init__(
            lower_bound,
            BIGINT64_MAX_POSITIVE,
            inclusive_lower=inclusive,
            inclusive_upper=True,
        )


class Less(Check):
    error_template = "Should be less than {1.upper_bound}"

    def __init__(self, upper_bound, inclusive=True):
        self.upper_bound = upper_bound
        self.inclusive = inclusive

    async def check(self, value, app):
        return value <= self.upper_bound if self.inclusive else value < self.upper_bound


class Greater(Check):
    error_template = "Should be greater than {1.lower_bound}"

    def __init__(self, lower_bound, inclusive=True):
        self.lower_bound = lower_bound
        self.inclusive = inclusive

    async def check(self, value, app):
        return value >= self.lower_bound if self.inclusive else value > self.lower_bound


class Custom(Check):
    def __init__(self, custom_fn):
        self.custom_fn = custom_fn

    async def check(self, value, app):
        return await self.custom_fn(value, app)


class Converter:
    error_template = "Failed to convert parameter to {1}: {2.__class__.__name__}({2})"

    @property
    def pretty_name(self):
        return self.__class__.__name__

    def __init__(self, default=None, checks=[]):
        self.default = default
        self.checks = checks

    async def convert(self, value, app):
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

    async def _convert(self, value, app):
        raise NotImplementedError

    def __str__(self):
        return self.pretty_name


class Integer(Converter):
    async def _convert(self, value, app):
        return int(value)


class ID(Integer):
    def __init__(self, **kwargs):
        check = BetweenXAndInt64(0)

        if "checks" not in kwargs:
            kwargs["checks"] = [check]
        else:
            kwargs["checks"].append(check)

        super().__init__(**kwargs)


class Number(Converter):
    async def _convert(self, value, app):
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            raise ValueError

        return result


class String(Converter):
    async def _convert(self, value, app):
        return value


class Boolean(Converter):
    POSITIVE = ["1", "y", "yes", "+", "positive"]
    NEGATIVE = ["0", "n", "no", "-", "negative"]

    async def _convert(self, value, app):
        lower_value = value.lower()

        if lower_value in self.POSITIVE:
            return True

        if lower_value in self.NEGATIVE:
            return False

        raise ValueError
