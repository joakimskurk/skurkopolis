#ifndef METRO_RESPONSE_FIXTURE_H
#define METRO_RESPONSE_FIXTURE_H
#include <sim_avr.h>
#include <stdio.h>
void response_fixture_init(avr_t *avr,const char *config);
void response_fixture_tick(avr_t *avr);
void response_fixture_report(FILE *out);
void response_fixture_close(avr_t *avr);
#endif
