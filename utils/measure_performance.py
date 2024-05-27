"""
Measures and records the performance metrics of a specified function.

This function is designed to capture the execution time, memory usage, and
CPU usage before and after the specified function is called. It appends
these metrics to a global list `performance_records`.

Parameters:
    func (callable): The function whose performance is to be measured.
    *args: Variable length argument list to be passed to the function `func`.
    **kwargs: Arbitrary keyword arguments to be passed to the function `func`.

Returns:
    The return value of the function `func`.

Side Effects:
    - Calls `gc.collect()` to perform garbage collection before measuring
    performance.
    - Appends a dictionary of performance metrics to the global list
    `performance_records`.
    - The performance metrics include:
        - `execution_time`: Time in seconds the function took to execute.
        - `memory_used`: Difference in memory used before and after function
        execution, in megabytes.
        - `cpu_usage_user`: Difference in CPU 'user' time before and after
        function execution.
        - `cpu_usage_system`: Difference in CPU 'system' time before and
        after function execution.
        - `cpu_usage_idle`: Difference in CPU 'idle' time before and after
        function execution.
"""

import time
import psutil
import gc


# List to hold all performance records
performance_records = []


def measure_performance(func, *args, **kwargs):
    gc.collect()  # Trigger garbage collection before measuring
    mem_before = psutil.virtual_memory().used
    cpu_times_before = psutil.cpu_times_percent(interval=1, percpu=False)

    start_time = time.time()
    result = func(*args, **kwargs)
    elapsed_time = time.time() - start_time

    cpu_times_after = psutil.cpu_times_percent(interval=1, percpu=False)
    mem_after = psutil.virtual_memory().used

    mem_used = (mem_after - mem_before) / (1024 * 1024)  # Convert bytes to MB
    cpu_used = {
        "user": cpu_times_after.user - cpu_times_before.user,
        "system": cpu_times_after.system - cpu_times_before.system,
        "idle": cpu_times_after.idle - cpu_times_before.idle,
    }

    # Append performance data to the list
    performance_records.append(
        {
            "execution_time": elapsed_time,
            "memory_used": mem_used,
            "cpu_usage_user": cpu_used["user"],
            "cpu_usage_system": cpu_used["system"],
            "cpu_usage_idle": cpu_used["idle"],
        }
    )

    return result
