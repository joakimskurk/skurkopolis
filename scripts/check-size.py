from pathlib import Path
import sys
row=Path(sys.argv[1] if len(sys.argv)>1 else 'build/avr/size.txt').read_text().splitlines()[-1].split()
text,data,bss=map(int,row[:3])
assert text+data < 26*1024, 'Flash budget exceeded'
assert data+bss < 1200, 'Static SRAM budget exceeded'
print('Budget PASS; stack and final HAL not measured. Compile-only harness, NOT hardware firmware.')
