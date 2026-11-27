"""A finite old-state side-information experiment through byte-framed ns.py ports."""
from itertools import product

import simpy
from ns.packet.packet import Packet
from ns.port.port import Port


def cells(t, early_label, split):
    low, high = max(t, 0), min(t + 7, 7)
    if split:
        low = max(low, 4 * early_label)
        high = min(high, 4 * early_label + 3)
    targets = list(range(low - 4, high + 5))
    labels = 2 if split else 4
    width = (len(targets) + labels - 1) // labels
    return [targets[i:i + width] for i in range(0, len(targets), width)]


def experiment(old, side, fresh, split, busy):
    env = simpy.Environment()
    # Time unit is ms. A rate of 8 bits/ms serializes one byte per ms.
    up, down = Port(env, 8), Port(env, 8)
    received, questions = simpy.Store(env), simpy.Store(env)
    class ReceiverPort:
        def put(self, packet):
            if packet.flow_id != 'background':
                received.put(packet)
    up.out, down.out = ReceiverPort(), questions
    ledger = []
    result = {}
    def transmit(port, kind, value, bits):
        size = 4 + (bits + 7) // 8
        packet = Packet(env.now, size, len(ledger), flow_id=kind, payload=value)
        ledger.append([kind, env.now, size, bits])
        port.put(packet)
    def source():
        label = old // 4 if split else None
        if split:
            transmit(up, 'early', label, 1)
        query = yield questions.get()
        yield env.timeout(20 - env.now)
        groups = cells(query.payload - 7, label, split)
        index = next(i for i, group in enumerate(groups) if fresh in group)
        transmit(up, 'fresh', index, 1 if split else 2)
    def receiver():
        label = None
        if split:
            msg = yield received.get()
            label = msg.payload
        yield env.timeout(10 - env.now)
        transmit(down, 'side', side + 7, 4)
        answer = yield received.get()
        group = cells(side, label, split)[answer.payload]
        result.update(time_ms=env.now, estimate=(min(group) + max(group)) / 2)
    def background():
        yield env.timeout(19)
        up.put(Packet(env.now, 10, 100, flow_id='background'))
    env.process(source())
    env.process(receiver())
    if busy:
        env.process(background())
    env.run()
    result.update(error=abs(result['estimate']-fresh), bytes=sum(p[2] for p in ledger),
                  deadline_met=result['time_ms'] <= 26)
    return result


def impossible_below_six():
    # For t=0 all old states are possible. Test all first-label partitions at width five.
    for tail in product((0, 1), repeat=7):
        labels = (0,) + tail
        feasible = True
        for a in set(labels):
            points = sorted({z for i in range(8) if labels[i]==a for z in range(i-4,i+5)})
            starts = []
            for z in points:
                if not starts or z >= starts[-1]+5:
                    starts.append(z)
            if len(starts)>2:
                feasible = False
                break
        assert not feasible


def run():
    impossible_below_six()
    rows = []
    for split, busy in product((True, False), repeat=2):
        for old in range(8):
            for side in range(old - 7, old + 1):
                for fresh in range(old - 4, old + 5):
                    value = experiment(old, side, fresh, split, busy)
                    rows.append(dict(split=split, busy=busy, old=old, side=side,
                                     fresh=fresh, **value))
    summary = []
    for split, busy in product((True, False), repeat=2):
        cases = [r for r in rows if r['split']==split and r['busy']==busy]
        error = max(r['error'] for r in cases)
        assert error == (2.5 if split else 1.5)
        summary.append(dict(schedule='1+1' if split else '0+2', busy=busy,
                            triples=len(cases), worst_error=error,
                            protocol_bytes=cases[0]['bytes'],
                            finish_ms=max(r['time_ms'] for r in cases),
                            deadline_misses=sum(not r['deadline_met'] for r in cases)))
    return rows, summary
