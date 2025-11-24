# C++ Time-Series Database (Insight-TSDB)

A high-performance time-series database engine built from scratch in C++ and exposed via a Python/FastAPI service. This project is a deep dive into the fundamentals of data engineering, focusing on single-machine performance, storage efficiency, and low-level system optimization.

The system is designed to ingest numerical time-series data, store it efficiently using custom compression, and query it with sub-millisecond latency.

## Key Features

- **Custom C++ Storage Engine**: Core logic is written in modern C++ (C++17) for direct control over memory layout and to avoid managed runtime overhead
- **High-Performance Querying**: A time-sharded storage architecture transforms slow, random disk reads into fast, sequential scans, enabling extremely low query latencies
- **Efficient Custom Compression**: Implemented time-series-specific compression algorithms (Delta-of-Delta for timestamps, XOR for values) from scratch to maximize storage efficiency
- **Modern API Layer**: A clean, documented RESTful API is provided using Python 3 and FastAPI for easy integration
- **Professional Tooling**: The project is fully containerized with Docker, built with CMake, and verified with a comprehensive Pytest and C++ unit testing suite

## System Architecture: The Write Path

The engine's design is inspired by a Log-Structured Merge-Tree (LSM-Tree) to optimize for high-throughput data ingestion while ensuring data durability.

1. **Ingest**: An API request is received
2. **Write-Ahead Log (WAL)**: The data point is immediately appended to a WAL on disk. This guarantees that even if the server crashes, no data will be lost
3. **Memtable**: The data point is simultaneously inserted into an in-memory table for fast access
4. **Query**: "Hot" queries for very recent data are served directly from the memtable at memory speed
5. **Flush & Compress**: Once the memtable is full, its contents are sorted, compressed, and flushed to a new, immutable time-shard file on disk

### Architecture Diagram
```md
flowchart TD

    %% =============================
    %%  API LAYER
    %% =============================
    Ingest[API Ingest Request]:::api
    Query[API Query Request]:::api

    %% =============================
    %%  WRITE PATH
    %% =============================
    Ingest --> WP[Write Path]:::process

    WP -->|1. Append to WAL (Disk)| WAL[(Write-Ahead Log)]:::disk
    WP -->|2. Insert into Memtable (RAM)| Memtable[(Memtable)]:::ram

    %% =============================
    %%  READ PATH (HOT QUERIES)
    %% =============================
    Query -->|3. Read recent data| Memtable

    %% =============================
    %%  FLUSH & COMPRESSION
    %% =============================
    Memtable -->|4. Flush when full| Comp[Compression Stage]:::process
    
    Comp -->|5. Write compressed shard (Disk)| Shard[(Time-Sharded .bin File)]:::disk

    %% =============================
    %%  STYLES
    %% =============================
    classDef api fill:#1f78b4,stroke:#0d4473,color:#fff,font-weight:bold;
    classDef process fill:#333,stroke:#111,color:#fff;
    classDef ram fill:#4caf50,stroke:#2e7d32,color:#fff;
    classDef disk fill:#6a1b9a,stroke:#4a126d,color:#fff;



 ```

## Technical Deep Dive: Design Decisions

The performance of this database is the result of specific, low-level design trade-offs made to optimize for the time-series use case.

### Why Time-Sharding?

The most common query pattern for time-series data is a short-range time scan. A traditional B-Tree index is inefficient for this. **Time-sharding transforms this problem from a slow, random-I/O disk operation into a blazing-fast, sequential scan** of a single, small, contiguous file that is likely already in the OS page cache.

### Why Custom Compression (Delta-of-Delta & XOR)?

Generic compression algorithms like Gzip are blind to data patterns. Time-series data is highly structured: timestamps are predictable, and values are often similar. By implementing these algorithms from scratch, we can exploit these patterns:

- **Delta-of-Delta** can reduce a 64-bit timestamp to just a few bytes
- **XOR compression** effectively stores only the changes in a floating-point value's bit pattern

This results in a storage footprint far smaller than what generic tools can achieve.

## Benchmark Analysis

### Benchmark Environment

All benchmarks were executed on the following developer-grade machine to ensure reproducibility:

- **CPU**: 12th Gen Intel(R) Core(TM) i7-12700H
- **RAM**: 16 GB
- **Storage**: 1Tb NVMe SSD Gen 4
- **OS**: Windows 11 Home (WSL2 Ubuntu 22.04)

### Performance Results

Benchmarks were run by ingesting and querying a dataset of 1,000,000 pseudo-realistic data points.

| Metric | Result | Analysis |
|--------|--------|----------|
| Storage Efficiency | ~8.2 bytes/point | A 50% reduction in storage compared to uncompressed 16-byte data points, achieved via custom compression on high-entropy data |
| Hot Query Latency (p99) | ~1.3 ms | Querying a 1-hour window of recent data. This validates the speed of the time-sharded architecture combined with OS page caching |
| Cold Query Latency (p99) | ~16 ms | Querying a 24-hour window of older data. Proves the design successfully avoids slow full-disk scans |
| Ingestion Throughput | ~5,500 points/sec | Baseline performance. The identified bottleneck is per-point file I/O overhead. The proposed optimization is a batch-ingestion API |

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/products/docker-desktop/)
- Git

### 1. Build the Docker Image

Clone the repository and run the docker build command from the project root:

```bash
git clone https://github.com/KaranSinghDev/cpp-time-series-database.git
cd cpp-time-series-database
docker build -t insight-service .
```

### 2. Run the Container

```bash
docker run -p 8000:8000 insight-service
```

The service is now running at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Local Development & Testing

### Prerequisites

- A C++17 compiler (g++) & CMake
- Python 3.10+ & pip

### 1. Build the C++ Engine

```bash
cd engine
cmake -B build
cmake --build build
```

### 2. Run the C++ Unit Tests

```bash
./engine/build/engine_test
```

### 3. Set Up & Run Python Tests

```bash
# From the project root
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
LD_LIBRARY_PATH=./engine/build pytest
```

## Technology Stack

- **Core Engine**: C++17
- **API Framework**: Python 3, FastAPI
- **Build System**: CMake
- **Testing**: Pytest (Python), C++ unit tests
- **Deployment**: Docker

## License

This project is provided as-is for educational and demonstration purposes.
