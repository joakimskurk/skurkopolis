import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from inspect_io_sites import inventory


class StaticSitesTests(unittest.TestCase):
    def test_synthetic_direct_accesses_and_callers(self):
        # Artificial instruction listing, no original-firmware bytes.
        source='''
   0:  00 e2        ldi r16, 0x20
   2:  05 b9        out 0x05, r16 ; 5
   4:  2b 98        cbi 0x05, 3 ; 5
   6:  1b 9b        sbis 0x03, 3 ; 3
   8:  8e b5        in r24, 0x2e ; 46
   a:  80 93 7a 00  sts 0x007a, r24
   e:  80 91 7c 00  lds r24, 0x007c
  12:  0e 94 20 00  call 0x40 ; 0x40
  16:  0c 94 30 00  jmp 0x60 ; 0x60
'''
        result=inventory(source,[0x40])
        self.assertEqual([x['register'] for x in result['ioSites']],
                         ['PORTB','PORTB','PINB','SPDR','ADCSRA','ADMUX'])
        self.assertEqual(result['ioSites'][1]['bit'],3)
        self.assertEqual(result['directAbsoluteCallers'],[{'pc':0x12,'kind':'call','target':0x40}])

    def test_non_io_indirect_and_labels_ignored(self):
        source='''
00000000 <label>:
  20:  80 81        ld r24, Z
  22:  80 93 00 01  sts 0x0100, r24
  26:  f9 cf        rjmp .-14 ; 0x1a
'''
        self.assertEqual(inventory(source,[0x1a]),{'ioSites':[],'directAbsoluteCallers':[]})


if __name__=='__main__':unittest.main()
