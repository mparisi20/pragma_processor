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

import argparse
import subprocess
import struct

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


"""

preproc_source = source
if -fix-regswaps:
    open source read-only, load contents into buffer
    preproc_source = name of newly created write-only file (with statement)
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

# TODO: make this more compact? Avoid hardcoding every instruction?

# 6-bit opcode field
opcode_map = {
               frozenset(14, 12, 13, 15, 7, 8, 28, 29, 24, 25, 
                26, 27, 20, 21, 34, 35, 42, 43, 40, 41, 
                32, 33, 38, 39, 44, 45, 36, 37, 46, 47, 
                50, 51, 48, 49, 54, 55, 52, 53, 56, 57, 
                60, 61): (6, 11),

               frozenset(11, 10, 3): (11),

               frozenset(23): (6, 11, 16)
             }

# 10-bit extended opcode field
op31_ext_map = {
                 frozenset(0, 32, 4, 86, 470, 54, 278, 246, 1014, 982): (11, 16),

                 frozenset(28, 60, 284, 476, 124, 444, 412, 316, 24, 792, 
                  536, 119, 87, 375, 343, 311, 279, 55, 23, 247, 
                  215, 439, 407, 183, 151, 790, 534, 918, 662, 533, 
                  661, 20, 150, 631, 599, 567, 535, 759, 727, 983, 
                  695, 663, 310, 438): (6, 11, 16), 

                 frozenset(26, 954, 922, 824, 597, 725): (6, 11),

                 frozenset(19, 83, 339, 371, 144, 146, 467, 595, 210): (6),

                 frozenset(659, 242): (6, 16),

                 frozenset(306): (16)
               }

# lower 9 bits
op31_ext_mask9_map = {
                       frozenset(266, 10, 138, 491, 459, 75, 11, 235, 40, 8, 136): (6, 11, 16),
                       frozenset(234, 202, 104, 232, 200): (6, 11)
                     }

# 10-bit extended opcode field
op63_ext_map = { 
                 frozenset(14, 15, 12, 264, 72, 136, 40): (6, 16),
                 frozenset(32, 0): (11, 16),
                 frozenset(583, 711): (6)
               }

# lower 5 bits
op63_ext_mask5_map = { 
                       (21, 18, 20): (6, 11, 16),
                       (25): (6, 11, 21),
                       (26): (6, 16),
                       (23, 29, 28, 31, 30): (6, 11, 16, 21)
                     }

# lower 5 bits
op59_ext_mask5_map = { 
                       frozenset(21, 18, 20): (6, 11, 16),
                       frozenset(25): (6, 11, 21),
                       frozenset(24): (6, 16),
                       frozenset(29, 28, 31, 30): (6, 11, 16, 21)
                     }

# 10-bit extended opcode field
op4_ext_map = { 
                frozenset(40, 72, 136, 264): (6, 16),
                frozenset(0, 32, 64, 96, 1014): (11, 16),
                frozenset(528, 560, 592, 624): (6, 11, 16)
              }

# lower 6 bits
op4_ext_mask6_map = { 
                      frozenset(6, 7, 38, 39): (6, 11, 16)
                    }

# lower 5 bits
op4_ext_mask5_map = { 
                      frozenset(18, 20, 21): (6, 11, 16),
                      frozenset(23, 28, 29, 30, 31, 10, 11, 14, 15): (6, 11, 16, 21),
                      frozenset(24, 26): (6, 16),
                      frozenset(25, 12, 13): (6, 11, 21)
                    }

class PPCInstr:

    instr_size = 32

    def __init__(self, val):
        self.v = val
    
    def get_field(self, left, right):
        return (self.v >> (self.instr_size - right - 1)) & ((1 << (right - left + 1)) - 1)
    
    def get_opcode(self):
        return self.get_field(0, 5)
        
    def get_ext_opcode(self):
        return self.get_field(21, 30)
    
    # map opcode/extended opcode to bit positions of register fields
    # return a set
    def get_reg_fields(self):
        # get opcode
        opcode = self.get_opcode()
        # if opcode = 31, etc... get extended opcode
        if opcode = 31:
            ext_opcode = self.get_ext_opcode()
            ext_opcode_masked = ext_opcode & 0x1ff
            for k in op31_map.keys():
                if ext_opcode in k:
                    return op31_map[k]
            
            # check with mask
            for k in op31_mask1_map.keys():
                if ext_opcode_masked in k:
                    return op31_mask1_map[k]
            
        elif opcode = 59:
            
        elif opcode = 63:
        
        elif opcode = 4:
        
        else:
        
        # 14 instructions have an OE bit, all have opcode 31, OE bit
        # doesn't create ambiguity with extended opcode
        # CANNOT just ignore bit 21 (e.g. lwzx vs lfsx)
        
        
        
        
        
        # return tuple of register field positions



    

x = PPCInstr(0x7C000214)
print(x.get_opcode())











