import ctypes
import os
import time
import random
import shutil
import numpy as np

# --- Configuration ---
# These parameters control the scale of the benchmark.
# 1 million points is a good baseline for a meaningful test.
NUM_POINTS = 1_000_000
NUM_QUERIES = 100  # Number of queries to run for statistical analysis

DATA_DIRECTORY = "data"

# --- C++ Bridge Setup ---
class CDataPoint(ctypes.Structure):
    _fields_ = [("timestamp", ctypes.c_uint64), ("value", ctypes.c_double)]

try:
    lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "engine", "build", "libinsight.so")
    lib = ctypes.CDLL(lib_path)
except OSError:
    print(f"FATAL: Could not load C++ library at {lib_path}")
    print("Please ensure the engine is compiled ('cmake --build build' in 'engine/' directory).")
    exit(1)

ingest_point_func = lib.ingest_point
ingest_point_func.argtypes = [ctypes.c_uint64, ctypes.c_double]
ingest_point_func.restype = None

query_range_func = lib.query_range
query_range_func.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.POINTER(CDataPoint), ctypes.c_int64]
query_range_func.restype = ctypes.c_int64

# --- Helper Functions ---
def get_dir_size(path='.'):
    """Calculates the total size of a directory in bytes."""
    total = 0
    for entry in os.scandir(path):
        if entry.is_file():
            total += entry.stat().st_size
        elif entry.is_dir():
            total += get_dir_size(entry.path)
    return total

def print_stats(label, latencies_ms):
    """Calculates and prints latency statistics."""
    p99 = np.percentile(latencies_ms, 99)
    avg = np.mean(latencies_ms)
    min_lat = np.min(latencies_ms)
    max_lat = np.max(latencies_ms)
    print(f"  - {label}:")
    print(f"    - Avg: {avg:.4f} ms")
    print(f"    - Min: {min_lat:.4f} ms")
    print(f"    - Max: {max_lat:.4f} ms")
    print(f"    - p99: {p99:.4f} ms (99% of requests were faster than this)")

# --- Benchmark Functions ---
def run_ingestion_benchmark():
    print(f"\n--- 1. Ingestion Benchmark ({NUM_POINTS:,} points) ---")
    points_to_ingest = []
    start_ts = int(time.time() * 1000)
    for i in range(NUM_POINTS):
        timestamp = start_ts + (i * 1000)
        value = 50.0 + 20.0 * (np.sin(i / 100.0)) + random.uniform(-1.0, 1.0)
        points_to_ingest.append((timestamp, value))

    start_time = time.perf_counter()
    for ts, val in points_to_ingest:
        ingest_point_func(ts, val)
    end_time = time.perf_counter()

    duration_s = end_time - start_time
    points_per_second = NUM_POINTS / duration_s
    print(f"RESULT: Ingested {NUM_POINTS:,} points in {duration_s:.2f} seconds.")
    print(f"  => Throughput: {points_per_second:,.0f} points/sec")
    return points_to_ingest

def run_storage_benchmark():
    print(f"\n--- 2. Storage Efficiency Benchmark ---")
    uncompressed_size = NUM_POINTS * 16  # 8 bytes for timestamp, 8 for value
    compressed_size = get_dir_size(DATA_DIRECTORY)
    bytes_per_point = compressed_size / NUM_POINTS
    compression_ratio = uncompressed_size / compressed_size

    print(f"RESULT: On-disk size for {NUM_POINTS:,} points is {compressed_size / (1024*1024):.2f} MB.")
    print(f"  - For comparison, uncompressed size would be {uncompressed_size / (1024*1024):.2f} MB.")
    print(f"  => Average Bytes per Point: {bytes_per_point:.2f}")
    print(f"  => Compression Ratio: {compression_ratio:.1f}x")

def run_query_benchmark(all_points):
    print(f"\n--- 3. Query Latency Benchmark ({NUM_QUERIES} queries per test) ---")
    BUFFER_CAPACITY = 1_000_000 
    BufferArrayType = CDataPoint * BUFFER_CAPACITY
    result_buffer = BufferArrayType()
    
    # --- Short-range, "hot" data query ---
    hot_latencies = []
    for _ in range(NUM_QUERIES):
        # Pick a random starting point near the end of the dataset
        start_index = random.randint(int(NUM_POINTS * 0.9), NUM_POINTS - 3601)
        query_start_ts = all_points[start_index][0]
        query_end_ts = query_start_ts + (3600 * 1000) # 1 hour
        
        start_time = time.perf_counter()
        query_range_func(query_start_ts, query_end_ts, result_buffer, BUFFER_CAPACITY)
        end_time = time.perf_counter()
        hot_latencies.append((end_time - start_time) * 1000)
    print_stats("Short-range Query (1 hour, 'hot' data)", hot_latencies)

    # --- Long-range, "cold" data query ---
    cold_latencies = []
    for _ in range(NUM_QUERIES):
        # Pick a random starting point in the first half of the dataset
        start_index = random.randint(0, int(NUM_POINTS * 0.5) - 86401)
        query_start_ts = all_points[start_index][0]
        query_end_ts = query_start_ts + (24 * 3600 * 1000) # 24 hours
        
        start_time = time.perf_counter()
        query_range_func(query_start_ts, query_end_ts, result_buffer, BUFFER_CAPACITY)
        end_time = time.perf_counter()
        cold_latencies.append((end_time - start_time) * 1000)
    print_stats("Long-range Query (24 hours, 'cold' data)", cold_latencies)

# --- Main Execution ---
if __name__ == "__main__":
    print("="*50)
    print("  Insight-TSDB Comprehensive Performance Benchmark")
    print("="*50)
    
    if os.path.exists(DATA_DIRECTORY):
        shutil.rmtree(DATA_DIRECTORY)
        
    ingested_points = run_ingestion_benchmark()
    run_storage_benchmark()
    run_query_benchmark(all_points=ingested_points)
    
    # Final cleanup
    if os.path.exists(DATA_DIRECTORY):
        shutil.rmtree(DATA_DIRECTORY)
    print("\nBenchmark complete. Cleanup finished.")