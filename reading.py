ENERGY_UNITS = ("wh", "kwh")


class Reading:
    """
    Reading represents an energy reading over an interval. It is essentially
    the same in concept as an ESPI IntervalBlock.
    """

    def __init__(self, start_time, end_time, unit, value):
        if start_time >= end_time:
            raise ValueError("end_time must be after start_time.")

        self.start_time = start_time
        self.end_time = end_time

        if unit.lower() not in ENERGY_UNITS:
            raise ValueError("Invalid unit: use only Wh or kWh.")

        if unit.lower() == "kwh":
            value = value * 1000

        self.wh = value

    @classmethod
    def combine(cls, a, b):
        return cls(
            a.start_time if a.start_time < b.start_time else b.start_time,
            a.end_time if a.end_time > b.end_time else b.end_time,
            "wh",
            a.wh + b.wh)

    def duration(self):
        return self.end_time - self.start_time

    def overlaps(self, other):
        return ((self.start_time < other.start_time and
                self.end_time > other.start_time) or
                (other.start_time < self.start_time and
                 other.end_time > self.start_time))

    def hash_bucket(self):
        return self.start_time.date

    def __eq__(self, them):
        return (isinstance(them, type(self)) and
                (self.start_time, self.end_time, self.wh) ==
                (them.start_time, them.end_time, them.wh))

    def __hash__(self):
        return hash((self.start_time, self.end_time, self.wh))

    def __str__(self):
        return f"Reading @ {self.start_time} ({self.duration()}): {self.wh} Wh"
