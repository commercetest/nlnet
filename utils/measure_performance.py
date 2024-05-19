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
