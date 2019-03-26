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
        # TODO: range checks for worker_id and datacenter_id
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        # TODO: use last_timestamp, start sequence from 0
        self.sequence = -1

    def gen_timestamp(self) -> int:
        return floor(time.time() * 1000) - EPOCH_OFFSET_MS

    def update_sequence(self) -> None:
        self.sequence = (self.sequence + 1) & SEQUENCE_MASK

    def gen_id(self) -> int:
        self.update_sequence()

        return int(
            (self.gen_timestamp() << TIMESTAMP_SHIFT)
            | (self.datacenter_id << DATACENTER_SHIFT)
            | (self.worker_id << WORKER_SHIFT)
            | self.sequence
        )
