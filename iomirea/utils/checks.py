

from constants import BIGINT64_MAX_POSITIVE


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
            lower_bound, BIGINT64_MAX_POSITIVE,
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
