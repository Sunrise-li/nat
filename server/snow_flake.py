#!/usr/bin/python3
import time
import logging

LOGGER                  = logging.getLogger('snowflake.log')

#64位ID 划分
WORKER_ID_BITS          = 5
DATACENTER_ID_BITS      = 5
SEQUENCE_BITS           = 12

#最大取值

MAX_WORKER_ID           = -1 ^ (-1 << WORKER_ID_BITS)
MAX_DATACENTER_ID       = -1 ^ (-1 << DATACENTER_ID_BITS)

##计算位偏移

WORKER_ID_OFFSET        = SEQUENCE_BITS
DATACENTER_ID_OFFSET    = SEQUENCE_BITS + WORKER_ID_BITS
TIMESTAMP_LEFT_OFFSET   = SEQUENCE_BITS +WORKER_ID_BITS + DATACENTER_ID_BITS

SEQUENCE_MASK           = -1 ^ (-1 << SEQUENCE_BITS)

#开始时间戳
TWEPOCH                 = 946656000000


class SnowFlake():
    def __init__(self,datacenter_id=0,worker_id=0,sequence=0):
        self.worker_id      = worker_id
        self.datacenter_id  = datacenter_id
        self.sequence       = sequence;
        self.last_time      = -1;

    def gen_time(self):
        return int(round(time.time() * 1000))

    def id(self):
        timestamp = self.gen_time()
        if timestamp == self.last_time:
            self.sequence = (self.sequence+1) & SEQUENCE_MASK
            if self.sequence == 0:
                timestamp = self.next_millis(self.last_time);
        else:
            self.sequence = 0

        self.last_time = timestamp;
        return ((timestamp- TWEPOCH) << TIMESTAMP_LEFT_OFFSET) \
            | (self.datacenter_id << DATACENTER_ID_OFFSET)\
                | (self.worker_id << WORKER_ID_BITS)\
                    | self.sequence


    def next_millis(self,last_time):
        timestamp = self.gen_time();
        while timestamp <= last_time:
            timestamp = self.gen_time()
        return timestamp
