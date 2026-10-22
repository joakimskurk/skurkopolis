// Synthetic protocol subset. No physical pin assignments or electrical claims.
#ifndef METRO_RESPONSE_PROTOCOL_H
#define METRO_RESPONSE_PROTOCOL_H
#include <stdint.h>
#include <stdbool.h>

typedef struct {
    bool initialized, stb, clk, open, invalid, command_seen, reading, ready;
    uint8_t shift, bits, command, page, address, read_bits, key[2], snapshot[2];
    uint8_t pages[4][6];
    bool display_on;
    uint64_t frames, commands, key_requests, key_complete, partial_reads;
    uint64_t write_bytes, unsupported, direction_faults, partial_bytes;
} metro_stled_t;
void metro_stled_init(metro_stled_t *s, uint8_t k0, uint8_t k1);
void metro_stled_update(metro_stled_t *s, bool stb, bool clk, bool host_drives,
                        bool data, bool gpio_valid);
bool metro_stled_output(const metro_stled_t *s, bool host_drives, bool *bit);

typedef struct {
    bool selected, invalid;
    uint8_t count, channel;
    uint16_t words[8], latched;
    uint64_t frames, complete, partial, malformed, responses;
    uint64_t channel_reads[8];
} metro_scan_t;
void metro_scan_select(metro_scan_t *s, bool selected);
bool metro_scan_exchange(metro_scan_t *s, uint8_t tx, uint8_t *rx);
#endif
