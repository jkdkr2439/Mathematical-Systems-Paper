"""Fixed-duration robust windows in two independent simulator traces."""
import math
from random import Random

import simpy
import pandapower as pp
import pandapower.networks as networks


def evaluate(values, width, quantum):
    """Report the first nominal maximizer, preserving ties in the oracle."""
    nominal = [((2 * v + quantum) // (2 * quantum)) * quantum for v in values]
    assert all(2 * abs(v - z) <= quantum for v, z in zip(values, nominal))
    windows = list(range(len(values) - width + 1))
    true_scores = [sum(values[i:i + width]) for i in windows]
    scores = [sum(nominal[i:i + width]) for i in windows]
    selected = max(windows, key=scores.__getitem__)
    competitors = [j for j in windows if j != selected]
    # Every coordinate unique to one interval contributes quantum/2 of error.
    spare = min(scores[selected] - scores[j] - min(width, abs(selected-j)) * quantum
                for j in competitors)
    disjoint_bound = min(scores[selected] - scores[j] for j in competitors) >= width * quantum
    regret = max(true_scores) - true_scores[selected]
    assert not (spare >= 0 and regret > 0)
    assert not disjoint_bound or spare >= 0
    return dict(width=width, quantum=quantum, selected=selected, regret=regret,
                certified=spare >= 0, margin=spare, coarse_certified=disjoint_bound)


def server_trace(seed):
    rng = Random(seed)
    env = simpy.Environment()
    cpu = simpy.Resource(env, capacity=1)
    latency = []
    def request(service, index):
        start = env.now
        with cpu.request() as token:
            yield token
            yield env.timeout(service)
        latency.append((index, env.now - start))
    def generate():
        for i in range(48):
            yield env.timeout(rng.randint(5, 14))
            service = rng.randint(4, 12) + (rng.randint(2, 7) if 14 <= i < 24 else 0)
            env.process(request(service, i))
    env.process(generate())
    env.run()
    assert len(latency) == 48
    return [t for _, t in sorted(latency)]


def power_traces():
    net = networks.case33bw()
    base_p, base_q = net.load.p_mw.copy(), net.load.q_mvar.copy()
    for seed in range(24):
        rng = Random(5000 + seed)
        samples, voltages = [], []
        phase = rng.uniform(-1.5, 1.5)
        for t in range(16):
            scale = .85 + .18 * math.cos((t - 7 - phase) * .5) + rng.uniform(-.045,.045)
            net.load['p_mw'] = base_p * scale
            net.load['q_mvar'] = base_q * scale
            pp.runpp(net, numba=False, init='results' if t else 'flat')
            assert net.converged
            # Meter at the substation after AC losses. 15 minutes per sample.
            samples.append(round(net.res_ext_grid.p_mw.sum() * 250000))  # Wh
            voltages.append(round(net.res_bus.vm_pu.min(), 6))
        yield dict(seed=seed, values=samples, min_voltage_pu=min(voltages))


def run():
    rows = []
    for seed in range(100):
        values = server_trace(seed)
        rows.append(dict(branch='server', seed=seed, unit='ms', values=values,
                         decisions=[evaluate(values, 6, q) for q in (2, 8, 24)]))
    for trace in power_traces():
        rows.append(dict(branch='power', unit='Wh', **trace,
                         decisions=[evaluate(trace['values'], 2, q) for q in (10000, 50000, 150000)]))
    summary = {}
    for branch in ('server', 'power'):
        cases = [r for r in rows if r['branch'] == branch]
        levels = sorted({a['quantum'] for r in cases for a in r['decisions']})
        summary[branch] = []
        for level in levels:
            tests = [a for r in cases for a in r['decisions'] if a['quantum'] == level]
            summary[branch].append(dict(quantum=level, traces=len(tests),
                certified=sum(a['certified'] for a in tests),
                coarse_certified=sum(a['coarse_certified'] for a in tests),
                nominal_wrong=sum(a['regret'] > 0 for a in tests),
                certified_wrong=sum(a['certified'] and a['regret'] > 0 for a in tests)))
    return rows, summary
