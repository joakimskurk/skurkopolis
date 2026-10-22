"""Firmware-level contracts for AVR master registers, independent of C internals."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from test_bus_trace import ROOT, inspect, hex_program, ldi, out
from test_response_fixture import read, bitop, spi_setup, transfer, profile


def write(address,value):
    return [ldi(value),out(address)]


def mark_status():
    # Copy a real CPU SPSR read to PORTD so the passive trace can observe it.
    return [read(0x2d),0xb800|(17<<4)|0x0b]


def irq_program(main):
    words=[0]*80
    words[0]=0xc000|79  # reset -> main
    words[34]=0xc000|(60-35)  # SPI_STC vector 17 -> ISR
    words[60:63]=mark_status()+[0x9518]  # RETI
    return words+write(0x3d,255)+write(0x3e,8)+main+[0xcfff]


@unittest.skipUnless(os.environ.get('RUN_CPU_TESTS')=='1','CPU inspector build required')
class SpiMasterTests(unittest.TestCase):
    def run_program(self,words,fixture=False,timing='avr-divider-v1',hz=16000000):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'test.hex';p.write_bytes(hex_program(words+[0xcfff]))
            f=Path(folder)/'fixture.json';f.write_text(json.dumps(profile()))
            kwargs=dict(spi_status='avr-master-v1',spi_timing=timing,hz=hz,fixture=f if fixture else None)
            a=inspect.inspect(p,ROOT/'build/cpu_inspector',10000,trace_limit=10000,**kwargs)['simulation']
            b=inspect.inspect(p,ROOT/'build/cpu_inspector',10000,**kwargs)['simulation']
            trace=a.pop('busTrace');self.assertEqual(a,b);self.assertFalse(trace['truncated'])
            self.assertEqual(a['stopReason'],'cycle_limit')
            marks=[e['value'] for e in trace['events'] if e['kind']=='write' and e['address']==0x2b]
            return a,trace['events'],marks

    def test_spif_needs_status_then_data_and_receive_buffer_persists(self):
        words=spi_setup()+[bitop(8,5,False)]+write(0x2e,0)+[0]*100
        words += [read(0x2e),read(0x2e)]+mark_status()+mark_status()+[read(0x2e)]+mark_status()+[read(0x2e)]
        s,e,m=self.run_program(words,fixture=True)
        self.assertEqual(m,[0x80,0x80,0])
        self.assertEqual([x['value'] for x in e if x['kind']=='read' and x['address']==0x4e],[0x12]*4)
        self.assertEqual(s['spiMaster']['spifAccessClears'],1)

    def test_status_read_before_completion_does_not_ack_future_spif(self):
        words=write(0x2c,0x50)+write(0x2e,0)+mark_status()+[0]*100+[read(0x2e)]+mark_status()
        _,_,m=self.run_program(words);self.assertEqual(m,[0,0x80])

    def test_spdr_write_does_not_unconditionally_clear_spif(self):
        words=write(0x2c,0x50)+write(0x2e,0)+[0]*100+write(0x2e,1)+mark_status()
        _,_,m=self.run_program(words);self.assertEqual(m,[0x80])

    def test_status_then_write_acknowledges_spif(self):
        words=write(0x2c,0x50)+write(0x2e,0)+[0]*100+mark_status()+write(0x2e,1)+mark_status()
        _,_,m=self.run_program(words);self.assertEqual(m,[0x80,0])

    def test_spsr_flags_read_only_reserved_zero_spi2x_writable(self):
        words=write(0x2d,255)+mark_status()+write(0x2c,0x50)+write(0x2e,0)+[0]*100
        words+=write(0x2d,0)+mark_status()+write(0x2d,255)+mark_status()
        _,_,m=self.run_program(words);self.assertEqual(m,[1,0x80,0x81])

    def test_collision_preserves_original_byte_deadline_and_fixture_transaction(self):
        words=spi_setup()+[bitop(8,5,False)]+write(0x2e,0)+write(0x2e,0xff)+[0]*100
        words+=mark_status()+[read(0x2e)]+mark_status()
        s,e,m=self.run_program(words,fixture=True)
        writes=[x for x in e if x['kind']=='write' and x['address']==0x4e]
        done=[x for x in e if x['kind']=='spi_output']
        self.assertEqual([x['value'] for x in done],[0]);self.assertEqual(done[0]['cycle']-writes[0]['cycle'],32)
        self.assertEqual(m,[0xc0,0]);self.assertEqual(s['spiMaster']['collisions'],1)
        self.assertEqual(s['responseFixture']['spiFaults'],0)
        self.assertEqual(s['responseFixture']['spiResponses'],1)
        self.assertEqual(s['spiMaster']['receiveByte'],0x12)

    def test_collision_ack_during_transfer_then_completion(self):
        words=write(0x2c,0x53)+write(0x2e,0)+write(0x2e,1)+mark_status()+[read(0x2e)]+mark_status()
        words += [0]*1100+mark_status()
        _,_,m=self.run_program(words);self.assertEqual(m,[0x40,0,0x80])

    def test_unread_receive_overwritten_only_on_next_completion(self):
        words=spi_setup()+[bitop(8,5,False)]+write(0x2e,0)+[0]*100+write(0x2e,0)+[0]*100+[read(0x2e),read(0x2e)]
        s,e,_=self.run_program(words,fixture=True)
        self.assertEqual(s['spiMaster']['unreadOverwrites'],1)
        self.assertEqual([x['value'] for x in e if x['kind']=='read' and x['address']==0x4e],[0x34,0x34])

    def test_receive_during_next_transfer_is_previous_byte(self):
        words=spi_setup()+[bitop(8,5,False)]+transfer(0)+write(0x2e,0)+[read(0x2e)]+[0]*100+[read(0x2e)]
        _,e,_=self.run_program(words,fixture=True)
        self.assertEqual([x['value'] for x in e if x['kind']=='read' and x['address']==0x4e],[0x12,0x12,0x34])

    def test_disabled_slave_writes_do_not_start_master_and_disable_aborts(self):
        words=write(0x2e,3)+write(0x2c,0x40)+write(0x2e,4)+write(0x2c,0x50)+write(0x2e,5)
        words+=write(0x2c,0)+write(0x2c,0x50)+[0]*100+mark_status()+transfer(6)
        s,e,m=self.run_program(words)
        self.assertEqual(m,[0]);self.assertEqual([x['value'] for x in e if x['kind']=='spi_output'],[6])
        self.assertEqual(s['spiMaster']['ignoredNonMasterWrites'],2)
        self.assertEqual(s['spiMaster']['abortedTransfers'],1)

    def test_interrupt_entry_clears_spif_and_late_enable_services_flag(self):
        for late in (False,True):
            main=write(0x2c,0x50 if late else 0xd0)+[0x9478]+write(0x2e,0)+[0]*100
            if late:main+=write(0x2c,0xd0)
            main += [0]*100+mark_status()
            s,_,m=self.run_program(irq_program(main))
            self.assertEqual(m,[0,0]);self.assertEqual(s['spiMaster']['isrEntries'],1)

    def test_flag_ack_cancels_pending_interrupt_before_sei(self):
        main=write(0x2c,0xd0)+write(0x2e,0)+[0]*100+mark_status()+[read(0x2e),0x9478]+[0]*100+mark_status()
        s,_,m=self.run_program(irq_program(main))
        self.assertEqual(m,[0x80,0]);self.assertEqual(s['spiMaster']['isrEntries'],0)

    def test_interrupt_entry_preserves_wcol_and_two_transfers_service_twice(self):
        main=write(0x2c,0xd0)+[0x9478]+write(0x2e,1)+write(0x2e,2)+[0]*100
        main += [read(0x2e)]+write(0x2e,3)+[0]*100
        s,_,m=self.run_program(irq_program(main))
        self.assertEqual(m,[0x40,0]);self.assertEqual(s['spiMaster']['isrEntries'],2)
        self.assertEqual(s['spiMaster']['collisions'],1)

    def test_new_collision_after_ack_is_not_lost(self):
        words=write(0x2c,0x53)+write(0x2e,0x11)+write(0x2e,0x22)+mark_status()
        words+=write(0x2e,0x33)+mark_status()+[0]*1100+mark_status()
        s,e,m=self.run_program(words)
        self.assertEqual(m,[0x40,0x40,0xc0]);self.assertEqual(s['spiMaster']['collisions'],2)
        self.assertEqual([x['value'] for x in e if x['kind']=='spi_output'],[0x11])

    def test_abort_fixture_transaction_then_new_select_recovers(self):
        words=spi_setup()+[bitop(8,5,False)]+write(0x2e,0)+write(0x2c,0)
        words += [bitop(8,5,True),bitop(8,5,False)]+write(0x2c,0x50)+transfer(8)+transfer(0)
        s,e,_=self.run_program(words,fixture=True)
        self.assertEqual([x['value'] for x in e if x['kind']=='read' and x['address']==0x4e],[0xab,0xcd])
        self.assertEqual(s['spiMaster']['abortedTransfers'],1)
        self.assertEqual(s['responseFixture']['spiFaults'],0)

    def test_all_dividers_both_frequencies_and_fixed_timing(self):
        for hz in (8000000,16000000):
            for timing in (None,'avr-divider-v1'):
                for index,div in enumerate((4,16,64,128,2,8,32,64)):
                    words=write(0x2c,0x50|(index&3))+write(0x2d,index>>2)+write(0x2e,0xa5)+[0]*1700
                    _,e,_=self.run_program(words,timing=timing,hz=hz)
                    start=next(x for x in e if x['kind']=='write' and x['address']==0x4e)
                    done=next(x for x in e if x['kind']=='spi_output')
                    self.assertEqual(done['cycle']-start['cycle'],8*div if timing else hz//10000)

    def test_invalid_profile_requires_runner(self):
        with self.assertRaises(ValueError):inspect.inspect('unused',spi_status='wrong')
        with self.assertRaises(ValueError):inspect.inspect('unused',spi_status='avr-master-v1')


if __name__=='__main__':unittest.main()
