// Passive, bounded observations of simavr 1.6 callbacks, not physical waveforms.
#ifndef METRO_BUS_TRACE_H
#define METRO_BUS_TRACE_H
#include <sim_avr.h>
#include <stdio.h>
#include <stdint.h>
void bus_trace_init(avr_t *avr, uint32_t capacity, uint64_t start);
void bus_trace_report(FILE *out);
void bus_trace_close(avr_t *avr);
#endif
