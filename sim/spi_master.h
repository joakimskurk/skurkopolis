#ifndef METRO_SPI_MASTER_H
#define METRO_SPI_MASTER_H
#include <sim_avr.h>
#include <stdbool.h>
#include <stdio.h>
void spi_master_init(avr_t *avr,bool divider_timing);
bool spi_master_enabled(void);
bool spi_master_can_start(avr_t *avr);
bool spi_master_busy(void);
void spi_master_receive(uint8_t value);
void spi_master_report(FILE *out);
void spi_master_close(avr_t *avr);
#endif
