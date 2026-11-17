from enum import Enum

class CacheTTL(Enum):

    VERY_SHORT = 30
    SHORT = 120
    MEDIUM = 300
    LONG = 900
    VERY_LONG = 3600