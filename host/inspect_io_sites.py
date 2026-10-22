"""Local static I/O-site inventory. No opcode bytes or disassembly are emitted."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile
from inspect_firmware import parse_hex

REGISTERS = {0x23:'PINB',0x24:'DDRB',0x25:'PORTB',0x26:'PINC',0x27:'DDRC',0x28:'PORTC',
             0x29:'PIND',0x2a:'DDRD',0x2b:'PORTD',0x4c:'SPCR',0x4d:'SPSR',0x4e:'SPDR',
             0x78:'ADCL',0x79:'ADCH',0x7a:'ADCSRA',0x7b:'ADCSRB',0x7c:'ADMUX'}


def inventory(disassembly, entries):
    sites, callers = [], []
    for line in disassembly.splitlines():
        match = re.match(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+([a-z]+)\s+(.*)$',line)
        if not match:
            continue
        pc, mnemonic, operand = int(match[1],16), match[2], match[3].split(';')[0].strip()
        operands = [x.strip() for x in operand.split(',')]
        address = None
        try:
            if mnemonic in ('out','sbi','cbi','sbis','sbic'):
                address = int(operands[0],0) + 0x20
            elif mnemonic == 'in':
                address = int(operands[1],0) + 0x20
            elif mnemonic == 'sts':
                address = int(operands[0],0)
            elif mnemonic == 'lds':
                address = int(operands[1],0)
            elif mnemonic in ('call','jmp') and int(operands[0],0) in entries:
                callers.append({'pc':pc,'kind':mnemonic,'target':int(operands[0],0)})
        except (ValueError, IndexError):
            continue
        if address in REGISTERS:
            item = {'pc':pc,'operation':mnemonic,'dataAddress':address,'register':REGISTERS[address]}
            if mnemonic in ('sbi','cbi','sbis','sbic'):
                item['bit'] = int(operands[1],0)
            sites.append(item)
    return {'ioSites':sites,'directAbsoluteCallers':callers}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('hex',type=Path)
    p.add_argument('--objdump',default='avr-objdump')
    p.add_argument('--entry',type=lambda x:int(x,0),action='append',default=[])
    args=p.parse_args()
    try:
        image,metadata=parse_hex(args.hex.read_bytes())
        with tempfile.TemporaryDirectory(prefix='metropolis-static-') as folder:
            binary=Path(folder)/'flash.bin';binary.write_bytes(image)
            run=subprocess.run([args.objdump,'-m','avr','-b','binary','-D',str(binary)],
                               capture_output=True,text=True,timeout=30,check=True)
        result=inventory(run.stdout,args.entry)
        result.update(input=metadata,boardEmulated=False,scope='static_candidates_only',
                      limitations=['Linear disassembly may decode data as instructions.',
                                   'Indirect accesses/calls and relative branches are not resolved.',
                                   'Only absolute callers to explicitly requested entries are listed.',
                                   'Runtime traces must establish execution; no physical wiring is proven.'])
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,subprocess.SubprocessError) as exc:
        p.exit(1,str(exc)+'\n')


if __name__=='__main__':main()
