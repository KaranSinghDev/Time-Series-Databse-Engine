#include "shard.h" // Our new header
#include <string>
#include <vector>
#include <filesystem>

const uint64_t SHARD_DURATION_MS = 3600000; // 1 hour
const std::string DATA_DIRECTORY = "data";

std::string get_shard_path(uint64_t timestamp) {
    uint64_t shard_start_ts = (timestamp / SHARD_DURATION_MS) * SHARD_DURATION_MS;
    uint64_t shard_end_ts = shard_start_ts + SHARD_DURATION_MS - 1;
    std::filesystem::create_directory(DATA_DIRECTORY);
    return DATA_DIRECTORY + "/" + std::to_string(shard_start_ts) + "-" + std::to_string(shard_end_ts) + ".bin";
}

extern "C" {
    // The ingest function now delegates to the ShardWriter class.
    void ingest_point(uint64_t timestamp, double value) {
        std::string file_path = get_shard_path(timestamp);
        ShardWriter writer(file_path);
        writer.append({timestamp, value});
        writer.close();
    }

    // The query function now delegates to the ShardReader class.
    int64_t query_range(uint64_t start_ts, uint64_t end_ts, DataPoint* out_buffer, int64_t buffer_capacity) {
        int64_t points_found = 0;
        uint64_t first_shard_start = (start_ts / SHARD_DURATION_MS) * SHARD_DURATION_MS;
        uint64_t last_shard_start = (end_ts / SHARD_DURATION_MS) * SHARD_DURATION_MS;

        for (uint64_t shard_start = first_shard_start; shard_start <= last_shard_start; shard_start += SHARD_DURATION_MS) {
            uint64_t shard_end = shard_start + SHARD_DURATION_MS - 1;
            std::string file_path = DATA_DIRECTORY + "/" + std::to_string(shard_start) + "-" + std::to_string(shard_end) + ".bin";
            
            if (!std::filesystem::exists(file_path)) continue;

            ShardReader reader(file_path);
            std::vector<DataPoint> points = reader.read_all();

            // Filter the decompressed points and copy to the output buffer.
            for (const auto& point : points) {
                if (points_found < buffer_capacity && point.timestamp >= start_ts && point.timestamp <= end_ts) {
                    out_buffer[points_found] = point;
                    points_found++;
                }
            }
        }
        return points_found;
    }
}