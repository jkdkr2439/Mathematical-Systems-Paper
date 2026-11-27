"""Independent RTL output compared with a shrinking-budget software monitor."""
from itertools import product
from random import Random

import pyrtl


def run():
    pyrtl.reset_working_block()
    q = pyrtl.Register(16, 'q')
    shift = pyrtl.Input(1, 'shift')
    out = pyrtl.Output(1, 'out')
    out <<= q[0]
    mask = 0x8001
    q.next <<= pyrtl.select(shift, pyrtl.concat(q[0], q[1:16]), q ^ mask)

    def trace(initial, ops):
        sim = pyrtl.Simulation(register_value_map={q: initial}, tracer=None)
        observed = []
        for op in (*ops, 0):
            sim.step({'shift': op})
            observed.append(sim.inspect('out'))
        return observed

    rng = Random(2121)
    states = sorted(set(range(32)) | {rng.randrange(65536) for _ in range(128)})
    rows = []
    for state in states:
        for ops in product((0, 1), repeat=3):
            observed = trace(state, ops)
            short = state & 15
            predicted = [short & 1]
            for step, op in enumerate(ops, 1):
                short = (short >> 1 if op else short ^ mask) & ((1 << (4-step))-1)
                predicted.append(short & 1)
            assert observed == predicted
            rows.append(dict(state=state, ops=ops, rtl=observed, monitor=predicted))
    profiles = {tuple(trace(s,(1,1,1))) for s in range(16)}
    assert len(profiles)==16
    witness = {str(s):trace(s,(1,1,1,1)) for s in (0,16)}
    assert witness['0'][:-1]==witness['16'][:-1] and witness['0'][-1]!=witness['16'][-1]
    return rows, dict(states=len(states), words=8, trajectories=len(rows),
                      comparisons=4*len(rows), mismatches=0, distinguishable=len(profiles),
                      four_shift_witness=witness)
