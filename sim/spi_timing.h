#ifndef METRO_SPI_TIMING_H
#define METRO_SPI_TIMING_H
#include <sim_avr.h>
#include <stdio.h>
void spi_timing_init(avr_t *avr);
void spi_timing_report(FILE *out);
void spi_timing_close(avr_t *avr);
const char *spi_timing_name(void);
#endif
