from time import thread_time_ns  # this way of calling thread_time_ns is faster
import sys
import gc
import statistics


def t(func):
    """Returns what the last func() call returns. This should help to notice if func() doesn't return the same value each time and detect that it does different things
    TODO: save resutls to file to compare first and second runs
    C++: https://stackoverflow.com/a/21995693 2 - Instrumentation"""
    def wrapper(*arg, **kw):
        with _Disable():
            timings, nruns, _ = _benchmark(func, *arg, **kw)
        normalized = [dur / nruns for dur in timings]
        var1 = statistics.variance(normalized)
        with _DisableSwitch():
            timings2, nruns, ret = _benchmark(func, *arg, **kw)
        normalized2 = [dur / nruns for dur in timings2]
        var2 = statistics.variance(normalized2)
        _plot(timings, normalized, max(timings + timings2))
        print()
        _plot(timings2, normalized2, max(timings + timings2))
        print(f"{_ns_str(min(normalized + normalized2)) = }, {nruns = }")
        print(_ns_str(var1 - var2))
        return ret
    return wrapper


def _benchmark(func, *arg, **kw):
    dur = 0.0
    nruns = 1
    TIMEIT_AUTORANGE_NS = 2e8
    while dur < TIMEIT_AUTORANGE_NS:
        dur, ret = _clean_scope(nruns, func, *arg, **kw)
        nruns *= 2
    nruns //= 2
    timings = [dur]
    NREPEAT = 9
    for _ in range(NREPEAT - 1):
        dur, ret = _clean_scope(nruns, func, *arg, **kw)
        timings.append(dur)

    return timings, nruns, ret


def _ns_str(ns: int):
    if abs(ns) < 10**3:
        return f"{ns} ns"
    if abs(ns) < 10**6:
        return f"{ns * 1e-3:.1f} un"
    if abs(ns) < 10**9:
        return f"{ns * 1e-6:.1f} ms"
    return f"{ns * 1e-9:.1f} s"


def _clean_scope(nruns, func, *arg, **kw):
    start_point = thread_time_ns()
    for _ in range(nruns):
        ret = func(*arg, **kw)
    end_point = thread_time_ns()
    return end_point - start_point, ret


class _Disable:
    def __enter__(self):
        self.interval = sys.getswitchinterval()
        sys.setswitchinterval(float("inf"))
        self.enabled = gc.isenabled()
        gc.disable()
    def __exit__(self, *_):
        sys.setswitchinterval(self.interval)
        if self.enabled:
            gc.enable()


class _DisableSwitch:
    def __enter__(self):
        self.interval = sys.getswitchinterval()
        sys.setswitchinterval(float("inf"))
    def __exit__(self, *_):
        sys.setswitchinterval(self.interval)


def _plot(raw, normalized, largest):
    MAX_GRAPH = 70
    scale = MAX_GRAPH / largest
    for length, report in zip(raw, normalized):
        scaled = round(length * scale)
        # TODO: draw diff, draw using cariable symbolds, like 00112233445566778899aabb
        print("=" * scaled + " " * (MAX_GRAPH - scaled) + _ns_str(report))
