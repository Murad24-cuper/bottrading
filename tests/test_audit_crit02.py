import threading
import time
from types import SimpleNamespace
import pytest
from src.mt5_client import MT5CallProxy, MT5CallTimeoutError

def test_single_worker_thread_used_for_all_calls():
    thread_ids = []
    def record_thread():
        thread_ids.append(threading.get_ident())
        return "ok"

    module = SimpleNamespace(call_a=record_thread, call_b=record_thread)
    initial_threads = threading.active_count()
    proxy = MT5CallProxy(module, timeout=1.0)

    # Must have created exactly one worker thread
    assert proxy.is_single_worker() is True
    
    res1 = proxy.call_a()
    res2 = proxy.call_b()
    assert res1 == "ok" and res2 == "ok"
    assert len(thread_ids) == 2
    # Both calls must have executed on the exact same thread
    assert thread_ids[0] == thread_ids[1]
    # No extra threads should be left running per call
    assert threading.active_count() <= initial_threads + 1

def test_timed_out_call_marks_unhealthy_and_rejects_further_calls():
    marked = []
    def slow():
        time.sleep(0.1)
        return "slow"
    def fast():
        return "fast"

    module = SimpleNamespace(slow=slow, fast=fast)
    proxy = MT5CallProxy(module, timeout=0.02, unhealthy=lambda n, t: marked.append((n, t)))

    with pytest.raises(MT5CallTimeoutError):
        proxy.slow()

    assert marked == [("slow", 0.02)]
    # Next call must fail immediately as unhealthy without queueing or spawning threads
    with pytest.raises(MT5CallTimeoutError, match="unhealthy"):
        proxy.fast()
