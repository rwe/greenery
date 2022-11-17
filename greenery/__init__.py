from __future__ import annotations

# In theory this should just pull in the `parse` function, but it turns out
# that the act of performing any relative import suddenly makes EVERY MODULE
# AVAILABLE IN SCOPE?
# Ignore errors because we are in fact importing these values to re-export them
from .bound import INF, Bound  # noqa: F401
from .multiplier import PLUS, QM, STAR, Multiplier  # noqa: F401
from .parse import parse  # noqa: F401

# WHY ARE THESE MODULE OBJECTS IN SCOPE SUDDENLY? I DIDN'T ASK FOR THEM
# print(bound, fsm, charclass, rxelems)

# This, however, is the *function*, *not* its containing module object?
# print(parse)
