"""

./tools/compile/compile.py "$(CFLAGS)" -fix-regswaps

#pragma regswap start end regA regB startFile

pragma is only meaningful when you're trying to build a matching ROM.
Modders don't care about regswaps. They care about shiftability.
Modding projects must ignore #pragma regswap to avoid corrupting the ROM
(add a Makefile option, "make mod" or similar)

makefile executes...
$(CC) $(CFLAGS) -lang c++ -c -o $@ $<

$(PYTHON) $(COMPILE) $(CC) $(CFLAGS) $@ $< -fix-regswaps


"""

# compile.py 
# github.com/mparisi20

# usage: compile.py cc cflags source [-fix-regswaps]

# TODO: add instruction swap option

import sys
import argparse
import subprocess
import tempfile
import re

parser = argparse.ArgumentParser()
parser.add_argument("cc", 
                    help="path to a C/C++ compiler")
parser.add_argument("cflags", 
                    help="all flags and options to be invoked with cc")
parser.add_argument("output", 
                    help="path to the outputted object file")
parser.add_argument("source", 
                    help="path to the C/C++ source file")
parser.add_argument("-fix-regswaps", 
                    help="execute #pragma regswap", action="store_true")
args = parser.parse_args()

def parse_reg(str):
    if str[0] == 'r' or str[0] == 'f':
        reg = int(str[1:])
        if reg >= 0 and reg <= 31:
            return reg
    raise ValueError("Failed to parse register argument (can be r0...r31 or f0...f31)")

pragmas = []
with open(args.source, "r") as src, tempfile.NamedTemporaryFile(mode="w") as proc_src:
    regswap_pattern = re.compile("[ \t]*#pragma[ \t]+regswap")
    for line in src:
        if regswap_pattern.match(line):
            if args.fix_regswaps:
                params = line.split()[2:]
                if len(params) != 5:
                    raise ValueError("ERROR: " + len(params) + " arguments passed to #pragma regswap (expected 5)")
                start = int(params[0], base=16)
                end = int(params[1], base=16)
                regA = parse_reg(params[2])
                regB = parse_reg(params[3])
                start_file = int(params[4], base=16)
                if not (start % 4 == 0 and end % 4 == 0 and start_file % 4 == 0):
                    raise ValueError("Invalid start, end, or start_file arguments (should have 4 byte aligment)")
                if not (start >= start_file and end > start):
                    raise ValueError("Invalid start, end, or start_file arguments (end must be > start, and start >= start_file)")
                pragmas.append((start-start_file, end-start_file, regA, regB))
        else:
            proc_src.write(line)

    subprocess.run(" ".join([args.cc, args.cflags, "-o", args.output, proc_src.name]))

instrs = []



if args.fix_regswaps and len(pragmas) != 0:
    with open(args.output, "rb") as f:
        

# TODO: get .text size

for i in range(text_size / 4):
    instrs.append(PPCInstr(int.from_bytes(f.read(4), byteorder='big')))


"""
preproc_source = tempfile
if -fix-regswaps:
    open source read-only, load contents into buffer
    for each line in source
        if line starts with "#pragma regswap" (skip whitespace)
            parse arguments: start end regA regB startFile (hex hex dec dec hex, 4 align)
            compute file offsets, push regswap task to list
        else
            write line to preproc_source
    close source
    
execute cc cflags output preproc_source

if -fix-regswaps and len(regswap task list) != 0:
    open output for reading (binary)
    parse as ELF (optional?)
    get .text section size (unpack big endian int), load .text section into buffer
    for each regswap task
        for each instruction (unpacked as big endian ints) in (start, end] 
            parse instruction opcode and use it to locate register fields
            change all regA -> regB and regB -> regA from left to right?
            
    reopen output for writing (binary)
    write patched .text section back to output
"""

# TODO: don't do any of this work unless there are regswap tasks 
# TODO: make this more compact? Avoid hardcoding every instruction?

# 10-bit extension field for instructions with opcode 31
op31_map = {
             'mask': 0x3ff,
             'data':
             {
             frozenset([0, 32, 4, 86, 470, 54, 278, 246, 1014, 982]): (11, 16),

             frozenset([28, 60, 284, 476, 124, 444, 412, 316, 24, 792, 
              536, 119, 87, 375, 343, 311, 279, 55, 23, 247, 
              215, 439, 407, 183, 151, 790, 534, 918, 662, 533, 
              661, 20, 150, 631, 599, 567, 535, 759, 727, 983, 
              695, 663, 310, 438]): (6, 11, 16), 

             frozenset([26, 954, 922, 824, 597, 725]): (6, 11),

             frozenset([19, 83, 339, 371, 144, 146, 467, 595, 210]): (6),

             frozenset([659, 242]): (6, 16),

             frozenset([306]): (16)
             }
           }

# lower 9 bits
op31_mask9_map = {
                   'mask': 0x1ff,
                   'data':
                   {
                   frozenset([266, 10, 138, 491, 459, 75, 11, 235, 40, 8, 136]): (6, 11, 16),
                   frozenset([234, 202, 104, 232, 200]): (6, 11)
                   }
                 }

# 10-bit extension field for instructions with opcode 63
op63_map = { 
             'mask': 0x3ff,
             'data':
             {
             frozenset([14, 15, 12, 264, 72, 136, 40]): (6, 16),
             frozenset([32, 0]): (11, 16),
             frozenset([583, 711]): (6)
             }
           }

# lower 5 bits
op63_mask5_map = { 
                   'mask': 0x1f,
                   'data':
                   {
                   frozenset([21, 18, 20]): (6, 11, 16),
                   frozenset([25]): (6, 11, 21),
                   frozenset([26]): (6, 16),
                   frozenset([23, 29, 28, 31, 30]): (6, 11, 16, 21)
                   }
                 }

# lower 5 bits of the 10-bit extension field for instructions with opcode 59
op59_mask5_map = { 
                   'mask': 0x1f,
                   'data':
                   {
                   frozenset([21, 18, 20]): (6, 11, 16),
                   frozenset([25]): (6, 11, 21),
                   frozenset([24]): (6, 16),
                   frozenset([29, 28, 31, 30]): (6, 11, 16, 21)
                   }
                 }

# 10-bit extension field for instructions with opcode 4
op4_map = {
            'mask': 0x3ff,
            'data':
            {
            frozenset([40, 72, 136, 264]): (6, 16),
            frozenset([0, 32, 64, 96, 1014]): (11, 16),
            frozenset([528, 560, 592, 624]): (6, 11, 16)
            }
          }

# lower 6 bits
op4_mask6_map = {
                  'mask': 0x3f,
                  'data':
                  {
                  frozenset([6, 7, 38, 39]): (6, 11, 16)
                  }
                }

# lower 5 bits
op4_mask5_map = {
                  'mask': 0x1f,
                  'data':
                  {
                  frozenset([18, 20, 21]): (6, 11, 16),
                  frozenset([23, 28, 29, 30, 31, 10, 11, 14, 15]): (6, 11, 16, 21),
                  frozenset([24, 26]): (6, 16),
                  frozenset([25, 12, 13]): (6, 11, 21)
                  }
                }

# 6-bit opcode field for miscellaneous opcodes
misc_opcode_map = {
                    'mask': 0x3f,
                    'data':
                    {
                    frozenset([14, 12, 13, 15, 7, 8, 28, 29, 24, 25, 
                     26, 27, 20, 21, 34, 35, 42, 43, 40, 41, 
                     32, 33, 38, 39, 44, 45, 36, 37, 46, 47, 
                     50, 51, 48, 49, 54, 55, 52, 53, 56, 57, 
                     60, 61]): (6, 11),

                    frozenset([11, 10, 3]): (11),

                    frozenset([23]): (6, 11, 16)
                    }
                  }

class PPCInstr:

    instr_size = 32
    reg_field_size = 5

    def __init__(self, val):
        self.v = val
    
    def get_field(self, left, right):
        return (self.v >> (self.instr_size - right - 1)) & ((1 << (right - left + 1)) - 1)
    
    def set_field(self, left, right, val):
        width = right - left + 1
        mask = (1 << width) - 1
        shift = self.instr_size - width - left
        self.v = self.v & ~(mask << shift) | ((val & mask) << shift)
    
    def get_opcode(self):
        return self.get_field(0, 5)
    
    def get_ext_opcode(self):
        return self.get_field(21, 30)
    
    def search_opcode_maps(self, opcode, *maps):
        for map in maps:
            masked_opcode = opcode & map['mask']
            for k in map['data'].keys():
                if masked_opcode in k:
                    return map['data'][k]
    
    # returns a tuple containing the bit position of each register field
    # or None if the instruction does not use registers
    # TODO: exception handling?
    def get_reg_fields(self):
        opcode = self.get_opcode()
        ext_opcode = self.get_ext_opcode()
        if opcode == 31:
            return self.search_opcode_maps(ext_opcode, op31_map, op31_mask9_map)
        elif opcode == 59:
            return self.search_opcode_maps(ext_opcode, op59_mask5_map)
        elif opcode == 63:
            return self.search_opcode_maps(ext_opcode, op63_map, op63_mask5_map)
        elif opcode == 4:
            return self.search_opcode_maps(ext_opcode, op4_map, op4_mask6_map, op4_mask5_map)
        else:
            return self.search_opcode_maps(ext_opcode, misc_opcode_map)
    
    # edit the PPC instruction to swap the registers
    def swap_registers(self, regA, regB):
        reg_fields = self.get_reg_fields()
        if reg_fields is None:
            return
        for left in reg_fields:
            right = left + self.reg_field_size - 1
            currReg = self.get_field(left, right)
            if currReg == regA:
                self.set_field(left, right, regB)
            elif currReg == regB:
                self.set_field(left, right, regA)

