#ifndef SHARD_H
#define SHARD_H

#include <string>
#include <cstdint>
#include <vector>
#include <fstream>

struct DataPoint {
    uint64_t timestamp;
    double value;
} __attribute__((packed));

class ShardWriter {
public:
    explicit ShardWriter(const std::string& file_path);
    void append(const DataPoint& point);
    void close();
private:
    void initialize_state();
    std::fstream file;
    uint64_t prev_timestamp;
    uint64_t prev_timestamp_delta;
    uint64_t prev_value_xor;
};

class ShardReader {
public:
    explicit ShardReader(const std::string& file_path);
    std::vector<DataPoint> read_all();
    
    // --- FIX: Add a static helper function ---
    // This can be called without creating a ShardReader object.
    // It can operate on any input stream.
    static std::vector<DataPoint> read_all_points(std::istream& stream);

private:
    std::ifstream file;
};

#endif // SHARD_H