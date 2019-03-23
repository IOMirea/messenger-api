import time
from math import floor

from constants import EPOCH_OFFSET_MS


MAX_SEQUENCE = 2 ** 12 - 1


class SnowflakeGenerator:
    def __init__(self, datacenter_id: int = 0, machine_id: int = 0):
        self.datacenter_id = datacenter_id
        self.machine_id = machine_id
        self.sequence_number = -1

    def gen_timestamp(self) -> int:
        return floor(time.time() * 1000) - EPOCH_OFFSET_MS

    def update_sequence(self) -> int:
        if self.sequence_number == MAX_SEQUENCE:
            self.sequence_number = 0
        else:
            self.sequence_number += 1

        return self.sequence_number

    def gen_id(self) -> int:
        self.update_sequence()

        return int(
            (self.gen_timestamp() << 22)
            | (self.datacenter_id << 5)
            | (self.machine_id << 5)
            | (self.sequence_number << 12)
        )
