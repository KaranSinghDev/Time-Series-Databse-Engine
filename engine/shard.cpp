#include "shard.h"
#include <iostream>
#include <cstring>

// These helpers can now be used by our new static function.
uint64_t read_varint(std::istream& in) {
    uint64_t value = 0;
    int shift = 0;
    uint8_t byte;
    do {
        if (!in.get(reinterpret_cast<char&>(byte))) return 0;
        value |= static_cast<uint64_t>(byte & 0x7F) << shift;
        shift += 7;
    } while (byte >= 0x80);
    return value;
}

void write_varint(std::ostream& out, uint64_t value) {
    while (value >= 0x80) {
        out.put(static_cast<char>((value & 0x7F) | 0x80));
        value >>= 7;
    }
    out.put(static_cast<char>(value));
}

// --- NEW STATIC HELPER FUNCTION IMPLEMENTATION ---
std::vector<DataPoint> ShardReader::read_all_points(std::istream& stream) {
    std::vector<DataPoint> points;
    
    uint64_t prev_timestamp = 0;
    uint64_t prev_timestamp_delta = 0;
    uint64_t prev_value_xor = 0;

    while (stream.peek() != EOF) {
        DataPoint point;
        if (prev_timestamp == 0) {
            point.timestamp = read_varint(stream);
        } else {
            uint64_t zigzag_encoded = read_varint(stream);
            int64_t delta_of_delta = (zigzag_encoded >> 1) ^ (-(static_cast<int64_t>(zigzag_encoded & 1)));
            uint64_t current_delta = prev_timestamp_delta + delta_of_delta;
            point.timestamp = prev_timestamp + current_delta;
            prev_timestamp_delta = current_delta;
        }
        prev_timestamp = point.timestamp;

        uint64_t value_xor = read_varint(stream);
        uint64_t current_value_bits = value_xor ^ prev_value_xor;
        memcpy(&point.value, &current_value_bits, sizeof(point.value));
        prev_value_xor = current_value_bits;
        
        // If read_varint hit EOF, timestamp might be 0, we should not add it.
        if (point.timestamp != 0 || !points.empty()) {
            points.push_back(point);
        }
    }
    return points;
}

// --- ShardReader now uses the helper ---
ShardReader::ShardReader(const std::string& file_path) {
    this->file.open(file_path, std::ios::binary);
}
std::vector<DataPoint> ShardReader::read_all() {
    if (!file.is_open()) return {};
    return read_all_points(this->file);
}


// --- ShardWriter Implementation [ROBUST] ---
ShardWriter::ShardWriter(const std::string& file_path) {
    this->file.open(file_path, std::ios::in | std::ios::out | std::ios::binary);
    if (!this->file.is_open()) {
         this->file.open(file_path, std::ios::out | std::ios::binary | std::ios::trunc);
    }
    initialize_state();
}

void ShardWriter::initialize_state() {
    this->file.seekg(0, std::ios::end);
    if (this->file.tellg() == 0) {
        this->prev_timestamp = 0;
        this->prev_timestamp_delta = 0;
        this->prev_value_xor = 0;
        return;
    }
    this->file.seekg(0);
    
    // --- FIX: Use the new static helper function ---
    std::vector<DataPoint> points = ShardReader::read_all_points(this->file);
    
    if (!points.empty()) {
        const auto& last_point = points.back();
        this->prev_timestamp = last_point.timestamp;
        memcpy(&this->prev_value_xor, &last_point.value, sizeof(double));
        if (points.size() > 1) {
             const auto& second_last_point = points[points.size() - 2];
             this->prev_timestamp_delta = last_point.timestamp - second_last_point.timestamp;
        } else {
            this->prev_timestamp_delta = 0;
        }
    }
    // Clear any error flags (like EOF) on the stream so we can write to it.
    this->file.clear();
}

void ShardWriter::append(const DataPoint& point) {
    if (!file.is_open()) return;
    this->file.seekp(0, std::ios::end);

    if (this->prev_timestamp == 0) {
        write_varint(file, point.timestamp);
    } else {
        uint64_t current_delta = point.timestamp - this->prev_timestamp;
        int64_t delta_of_delta = static_cast<int64_t>(current_delta - this->prev_timestamp_delta);
        uint64_t zigzag_encoded = (delta_of_delta << 1) ^ (delta_of_delta >> 63);
        write_varint(file, zigzag_encoded);
        this->prev_timestamp_delta = current_delta;
    }
    this->prev_timestamp = point.timestamp;
    uint64_t current_value_bits;
    memcpy(&current_value_bits, &point.value, sizeof(point.value));
    uint64_t value_xor = current_value_bits ^ this->prev_value_xor;
    write_varint(file, value_xor);
    this->prev_value_xor = current_value_bits;
}

void ShardWriter::close() { if (file.is_open()) { file.close(); } }