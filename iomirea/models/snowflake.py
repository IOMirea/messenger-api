import time
from math import floor

from constants import EPOCH_OFFSET_MS


WORKER_BITS = 5
DATACENTER_BITS = 5
SEQUENCE_BITS = 12

MAX_WORKER_ID = -1 ^ (-1 << WORKER_BITS)
MAX_DATACENTER_ID = -1 ^ (-1 << DATACENTER_BITS)

WORKER_SHIFT = SEQUENCE_BITS
DATACENTER_SHIFT = SEQUENCE_BITS + WORKER_BITS
TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_BITS + DATACENTER_BITS

SEQUENCE_MASK = -1 ^ (-1 << SEQUENCE_BITS)


class SnowflakeGenerator:
    def __init__(self, worker_id: int = 0, datacenter_id: int = 0):
        if not 0 <= worker_id <= MAX_WORKER_ID:
            raise ValueError(
                f"Worker id should be between 0 and {MAX_WORKER_ID}"
            )

        if not 0 <= datacenter_id <= MAX_DATACENTER_ID:
            raise ValueError(
                f"Datacenter id should be between 0 and {MAX_DATACENTER_ID}"
            )

        self.worker_id = worker_id
        self.datacenter_id = datacenter_id

        self.sequence = 0

        self._last_timestamp = -1

    def gen_timestamp(self) -> int:
        return floor(time.time() * 1000)

    def til_next_ms(self) -> int:
        timestamp = self.gen_timestamp()
        while timestamp <= self._last_timestamp:
            timestamp = self.gen_timestamp()

        return timestamp

    def gen_id(self) -> int:
        timestamp = self.gen_timestamp()
        if timestamp < self._last_timestamp:
            raise RuntimeError(
                f"System clock went backwards, unable to generate ids for {self._last_timestamp - timestamp}"
            )

        if self._last_timestamp == timestamp:
            self.sequence = (self.sequence + 1) & SEQUENCE_MASK
            if self.sequence == 0:  # overflow
                timestamp = self.til_next_ms()
        else:
            self.sequence = 0

        self._last_timestamp = timestamp

        return int(
            ((timestamp - EPOCH_OFFSET_MS) << TIMESTAMP_SHIFT)
            | (self.datacenter_id << DATACENTER_SHIFT)
            | (self.worker_id << WORKER_SHIFT)
            | self.sequence
        )
