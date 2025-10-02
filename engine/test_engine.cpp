#include <iostream>
#include <fstream>
#include <cstdint>
#include <cassert>
#include <cstdio>
#include <vector>
#include <filesystem>

const uint64_t SHARD_DURATION_MS = 3600000;
const std::string DATA_DIRECTORY = "data";

struct DataPoint {
    uint64_t timestamp;
    double value;
} __attribute__((packed));

extern "C" {
    void ingest_point(uint64_t timestamp, double value);
    int64_t query_range(uint64_t start_ts, uint64_t end_ts, DataPoint* out_buffer, int64_t buffer_capacity);
}

void cleanup_test_data() {
    if (std::filesystem::exists(DATA_DIRECTORY)) {
        std::filesystem::remove_all(DATA_DIRECTORY);
    }
}

void setup_test_data() {
    cleanup_test_data();
    ingest_point(1000, 10.0);
    ingest_point(2000, 20.0);
    ingest_point(3600000, 30.0);
    ingest_point(4000000, 40.0);
    ingest_point(8000000, 50.0);
}

void test_sharded_queries() {
    std::cout << "Running C++ unit test for sharded query logic..." << std::endl;
    setup_test_data();

    const int BUFFER_SIZE = 10;
    DataPoint results[BUFFER_SIZE];

    // --- Test Case 1: Query within a single shard ---
    int64_t count = query_range(0, 3000, results, BUFFER_SIZE);
    assert(count == 2);
    assert(results[0].timestamp == 1000);
    assert(results[1].timestamp == 2000);
    
    // --- Test Case 2: Query spanning two shards ---
    count = query_range(1500, 3700000, results, BUFFER_SIZE);
    assert(count == 2);
    assert(results[0].timestamp == 2000);
    assert(results[1].timestamp == 3600000);

    // --- Test Case 3: Query spanning all three shards ---
    count = query_range(0, 9000000, results, BUFFER_SIZE);
    assert(count == 5);
    
    // --- Test Case 4: Query with no results ---
    count = query_range(12000000, 13000000, results, BUFFER_SIZE);
    assert(count == 0);

    cleanup_test_data();
    std::cout << "C++ Sharded Query Test PASSED!" << std::endl;
}

int main() {
    test_sharded_queries();
    return 0;
}