import timeit
from time import thread_time_ns  # this way of calling thread_time_ns is faster
import functools
import sys
import gc
import statistics
import time


def t(func):
    """Returns what the last func() call returns. This should help to notice if func() doesn't return the same value each time and detect that it does different things
    TODO: save resutls to file to compare first and second runs"""
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




def old(func):
    def wrapper(*arg, **kw):
        no_args = functools.partial(func, *arg, **kw)
        old = sys.getswitchinterval()
        sys.setswitchinterval(float("inf"))
        timer = timeit.Timer(no_args, timer=time.process_time)  # TODO: _ns
        rep_number, _ = timer.autorange()
        raw_timings = timer.repeat(number=rep_number)
        sys.setswitchinterval(old)
        def format_time(dt):
            unit = None
            units = {"ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0}

            if unit is not None:
                scale = units[unit]
            else:
                scales = [(scale, unit) for unit, scale in units.items()]
                scales.sort(reverse=True)
                for scale, unit in scales:
                    if dt >= scale:
                        break

            precision = 3
            return "%.*g %s" % (precision, dt / scale, unit)
        timings = [dt / rep_number for dt in raw_timings]
        print("raw times: %s" % ", ".join(map(format_time, timings)))

        best = min(timings)
        print("%d loop%s, best of %d: %s per loop"
            % (rep_number, 's' if rep_number != 1 else '',
                rep_number, format_time(best)))
        _plot(timings)
        return no_args()
    return wrapper


def _plot(raw, normalized, largest):
    MAX_GRAPH = 70
    scale = MAX_GRAPH / largest
    for length, report in zip(raw, normalized):
        scaled = round(length * scale)
        print("=" * scaled + " " * (MAX_GRAPH - scaled) + _ns_str(report))
