#! /usr/bin/env python3
#
# This file contains some functions to help encode MIPS16 instrctions. The instructions come in a
# bunch of formats, so this contains functions to help fill them out based on the MIPS16 datasheet
# and print them as hex bytes. The bytes are output in the same way as llvm-mc does so that this
# can aid in creating llvm-mc tests.

import random

# Common opcodes for a number of instruction formats. The EXTEND opcode applies to almost all 32-bit
# instructions--the only exception is JAL(X). I8, SHIFT, RR, and RRR are opcodes that apply to a few
# formats with sub-opcodes to indicate the function. RRI-A is used only for the "addi(u)" insstructions.
# SVRS is used for both the "save" and "restore" instructions. CNVT is used is some RR instructions
# to take a sub-sub-opcode instead of a second register.
RR_op = 0xE800
RRR_op = 0xE000
RRIA_op = 0x4000
SHIFT_op = 0x3000
I8_op = 0x6000
SVRS_op = 0x0400
JALRC_op = 0x0000
CNVT_op = 0x0011
EXTJAL_op = 0x18000000
EXTEND_op = 0xF0000000
#EXTRR_op = EXTEND_op | RR_op
EXTRRR_op = EXTEND_op | RRR_op
EXTRRIA_op = EXTEND_op | RRIA_op
EXTSHIFT_op = EXTEND_op | SHIFT_op
EXTI8_op = EXTEND_op | I8_op
EXTSVRS_op = EXTEND_op | SVRS_op

# Map MIPS32 and MIPS16 register names to the binary encodings in the instruction word. Registers
# in assembly can be referred to by their numbers or ABI register names, so $7 and $a3 are the same
# register.
MIPS32_REGS = {'$0' :  0, '$1' :  1, '$2' :  2, '$3 ':  3, '$4' :  4, '$5' :  5, '$6' :  6, '$7' :  7, 
               '$8' :  8, '$9' :  9, '$10': 10, '$11': 11, '$12': 12, '$13': 13, '$14': 14, '$15': 15,
               '$16': 16, '$17': 17, '$18': 18, '$19': 19, '$20': 20, '$21': 21, '$22': 22, '$23': 23,
               '$24': 24, '$25': 25, '$26': 26, '$27': 27, '$28': 28, '$29': 29, '$30': 30, '$31': 31,
             '$zero':  0, '$at':  1, '$v0':  2, '$v1':  3, '$a0':  4, '$a1':  5, '$a2':  6, '$a3':  7, 
               '$t0':  8, '$t1':  9, '$t2': 10, '$t3': 11, '$t4': 12, '$t5': 13, '$t6': 14, '$t7': 15,
               '$s0': 16, '$s1': 17, '$s2': 18, '$s3': 19, '$s4': 20, '$s5': 21, '$s6': 22, '$s7': 23,
               '$t8': 24, '$t9': 25, '$k0': 26, '$k1': 27, '$gp': 28, '$sp': 29, '$fp': 30, '$ra': 31}

MIPS32_KEYS = list(MIPS32_REGS.keys())

# Yes, MIPS16 really does use the names $16 and $17 and encodes them as 0 and 1, respectively.
# Also, $0 and $1 are invalid in MIPS16, probably for compatibility with the MIPS32 conventions.
MIPS16_REGS = {'$2' :  2, '$3 ':  3, '$4' :  4, '$5' :  5, '$6' :  6, '$7' :  7, '$16': 0, '$17': 1,
               '$v0':  2, '$v1':  3, '$a0':  4, '$a1':  5, '$a2':  6, '$a3':  7, '$s0': 0, '$s1': 1}

MIPS16_KEYS = list(MIPS16_REGS.keys())

def rand_mips16_reg():
    return random.choice(MIPS16_KEYS)

def rand_mips32_reg():
    return random.choice(MIPS32_KEYS)

def rand_imm(start, end, stride=1):
    return random.randrange(start, end+1, stride)     # +1 to include end in range


def verify_integer_argument(arg, arg_name, min_value, max_value, p2align):
    '''Verify that the argument falls within the given range and meets the given power-of-2 alignment.

    Check if the agument is within the given bounds and is aligned to 2 raised to "p2align". The 
    range is inclusive of the min and max values. If the alignment value is greater than zero, then
    this will check that the argument is a multiple of 2**p2align (or rather, that "arg modulo 
    (1<<p2align)" is zero).
 
    If not, this will raise a ValueError with a message containing the given name and the issue,
    whether the range or alignment is off. The range and alignment are also included in the message.
    '''
    if arg < min_value  or  arg > max_value:
        raise ValueError('Argument "' + str(arg_name) + '" (' + str(arg) + ') must be in range [' +
                         str(min_value) + ', ' + str(max_value) + ']')
    
    if p2align > 0  and  (arg % (1 << p2align)) != 0:
        raise ValueError('Argument "' + str(arg_name) + '" (' + str(arg) + ') must be ' +
                         str(1 << p2align) + '-byte aligned')

def verify_opcode(op, opname):
    '''Verify that the opcode or function, which should be a 5-bit unsigned value, is between 0
    and 31.
    '''
    verify_integer_argument(op, opname, 0, 31, 0)

def verify_15bit_signed_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 15-bit
    signed value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, -16384 << instr_shift, 16383 << instr_shift, instr_shift)

def verify_16bit_signed_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 16-bit
    signed value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, -32768 << instr_shift, 32767 << instr_shift, instr_shift)

def verify_11bit_signed_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects an 11-bit
    signed value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, -1024 << instr_shift, 1023 << instr_shift, instr_shift)

def verify_8bit_signed_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects an 8-bit
    signed value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, -128 << instr_shift, 127 << instr_shift, instr_shift)

def verify_8bit_unsigned_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects an 8-bit
    unsigned value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, 0, 255 << instr_shift, instr_shift)

def verify_5bit_unsigned_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 5-bit
    unsigned value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, 0, 31 << instr_shift, instr_shift)

def verify_4bit_signed_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 4-bit
    signed value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, -8 << instr_shift, 7 << instr_shift, instr_shift)

def verify_4bit_unsigned_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 4-bit
    unsigned value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, 0, 15 << instr_shift, instr_shift)

def verify_3bit_unsigned_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 3-bit
    unsigned value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, 0, 7 << instr_shift, instr_shift)

def verify_2bit_unsigned_value(imm, imm_name, instr_shift):
    '''Verify that the given value could be used in an instruction that expects a 2-bit
    unsigned value and that left-shifts the encoded value by instr_shift bits.
    '''
    verify_integer_argument(imm, imm_name, 0, 3 << instr_shift, instr_shift)

def verify_flag_bit(flag, flag_name):
    '''Verify that the given value could be used in an instruction that expects a 1-bit
    flag.
    '''
    verify_integer_argument(flag, flag_name, 0, 1, 0)


def extract_bits(i, end, start):
    '''Extract continuous bits from the given integer and return them in the least-significant bits
    of the result.

    This swaps start and end if start is larger. This shifts the integer right by start bits and
    uses the difference between start and end to create a mask which is ANDed against the result.
    The bits at positions start and end are included in the result.
    '''
    if start > end:
        start, end = end, start

    mask = (1 << (end - start + 1)) - 1
    return (i >> start) & mask


class Mips16Instr:
    def __init__(self, name):
        self._name = name
        self._args = ()
        self._encoding = 0
        self._is32bit = False

    def get_instr_string(self):
        instr_str = self._name
        args_strs = [str(s) for s in self._args]
        return instr_str + ' ' + ', '.join(args_strs)

    def get_encoding_as_bytes(self, byteorder):
        if self._is32bit:
            len = 4
        else:
            len = 2

        return self._encoding.to_bytes(len, byteorder)


class Mips16IInstr(Mips16Instr):
    def __init__(self, name, op, imm, instr_shift):
        super().__init__(name)
 
        verify_opcode(op, 'op')
        verify_11bit_signed_value(imm, 'imm', instr_shift)

        shifted_imm = imm >> instr_shift

        # This format is used only for branch instructions and the assembler expects the argument
        # to be odd to indicate that a jump to MIPS16 code is occurring. This does not appear to be
        # encoded in the instruction because it cannot jump to MIPS32.
        self._args = (imm | 0x01,)
        self._encoding = (op << 11) | (shifted_imm & 0x7FF)
        self._is32bit = False

class Mips16RIInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift, sign_ext):
        super().__init__(name)

        verify_opcode(op, 'op')

        if sign_ext:
            verify_8bit_signed_value(imm, 'imm', instr_shift)
        else:
            verify_8bit_unsigned_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        shifted_imm = imm >> instr_shift

        # Instructions starting with 'b' are branch instructions and the assembler expects their
        # immediate argument to be odd to indicate a jump to a MIPS16 instruction. Branch 
        # instructions cannot jump to MIPS32 mode, so the bit is not part of the encoding.
        if name.startswith('b'):
            imm = imm | 0x01

        self._args = (rx, imm)
        self._encoding = (op << 11) | (rx_num << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16RIpcrelInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_8bit_signed_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        shifted_imm = imm >> instr_shift

        self._args = (rx, '$pc', imm)
        self._encoding = (op << 11) | (rx_num << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16RIsprelInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_8bit_unsigned_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        shifted_imm = imm >> instr_shift

        self._args = (rx, '$sp', imm)
        self._encoding = (op << 11) | (rx_num << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16RIpcrelMemInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_8bit_unsigned_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        shifted_imm = imm >> instr_shift

        self._args = (rx, str(imm) + '($pc)')
        self._encoding = (op << 11) | (rx_num << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16RIsprelMemInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_8bit_unsigned_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        shifted_imm = imm >> instr_shift

        self._args = (rx, str(imm) + '($sp)')
        self._encoding = (op << 11) | (rx_num << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16RRInstr(Mips16Instr):
    def __init__(self, name, rx, ry, funct):
        super().__init__(name)

        verify_opcode(funct, 'funct')

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        self._args = (ry, rx)
        self._encoding = RR_op | (rx_num << 8) | (ry_num << 5) | (funct)
        self._is32bit = False

class Mips16RRhiloInstr(Mips16Instr):
    def __init__(self, name, rx, funct):
        super().__init__(name)

        verify_opcode(funct, 'funct')

        rx_num = MIPS16_REGS[rx]

        self._args = (rx,)
        self._encoding = RR_op | (rx_num << 8) | (funct)
        self._is32bit = False

class Mips16RRbreakInstr(Mips16Instr):
    def __init__(self, name, code, funct):
        super().__init__(name)

        verify_opcode(funct, 'funct')
        verify_integer_argument(code, 'code', 0, 63, 0)

        if 0 != code:
            self._args = (code,)

        self._encoding = RR_op | (code << 5) | (funct)
        self._is32bit = False

class Mips16RRjalrcInstr(Mips16Instr):
    def __init__(self, name, rx, subfunc_ry):
        super().__init__(name)

        verify_3bit_unsigned_value(subfunc_ry, 'subfunc_ry', 0)

        rx_num = MIPS16_REGS[rx]

        self._args = (rx,)
        self._encoding = RR_op | (rx_num << 8) | (subfunc_ry << 5) | JALRC_op
        self._is32bit = False

class Mips16RRjalrcraInstr(Mips16Instr):
    def __init__(self, name, subfunc_ry):
        super().__init__(name)

        verify_3bit_unsigned_value(subfunc_ry, 'subfunc_ry', 0)

        self._args = ('$ra',)
        self._encoding = RR_op | (subfunc_ry << 5) | JALRC_op
        self._is32bit = False

class Mips16RRcnvtInstr(Mips16Instr):
    def __init__(self, name, rx, subfunc_ry):
        super().__init__(name)

        verify_3bit_unsigned_value(subfunc_ry, 'subfunc_ry', 0)

        rx_num = MIPS16_REGS[rx]

        self._args = (rx,)
        self._encoding = RR_op | (rx_num << 8) | (subfunc_ry << 5) | CNVT_op
        self._is32bit = False

class Mips16RRIInstr(Mips16Instr):
    def __init__(self, name, op, rx, ry, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_5bit_unsigned_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]
        shifted_imm = imm >> instr_shift

        self._args = (ry, rx, imm)
        self._encoding = (op << 11) | (rx_num << 8) | (ry_num << 5) | (shifted_imm & 0x1F)
        self._is32bit = False

class Mips16RRIMemInstr(Mips16Instr):
    def __init__(self, name, op, rx, ry, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_5bit_unsigned_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]
        shifted_imm = imm >> instr_shift

        # Memory instructions like "lw" and "sw" have a special format, so handle it here
        self._args = (ry, str(imm) + '(' + str(rx) + ')')
        self._encoding = (op << 11) | (rx_num << 8) | (ry_num << 5) | (shifted_imm & 0x1F)
        self._is32bit = False

class Mips16RRRInstr(Mips16Instr):
    def __init__(self, name, rx, ry, rz, f):
        super().__init__(name)

        verify_2bit_unsigned_value(f, 'f', 0)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]
        rz_num = MIPS16_REGS[rz]

        self._args = (rz, ry, rx)
        self._encoding = RRR_op | (rx_num << 8) | (ry_num << 5) | (rz_num << 2) | (f)
        self._is32bit = False

class Mips16RRIAInstr(Mips16Instr):
    def __init__(self, name, rx, ry, f, imm):
        super().__init__(name)

        verify_flag_bit(f, 'f')
        verify_4bit_signed_value(imm, 'imm', 0)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        self._args = (ry, rx, imm)
        self._encoding = RRIA_op | (rx_num << 8) | (ry_num << 5) | (imm & 0x0F)
        self._is32bit = False

class Mips16ShiftInstr(Mips16Instr):
    def __init__(self, name, rx, ry, sa, f):
        super().__init__(name)

        verify_2bit_unsigned_value(f, 'f', 0)

        # sa ranges from 1 to 8 (8 is encoded as 0 in the instruction)
        verify_integer_argument(sa, 'sa', 1, 8, 0)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        self._args = (ry, rx, sa)
        self._encoding = SHIFT_op | (rx_num << 8) | (ry_num << 5) | ((sa & 0x07) << 2) | (f)
        self._is32bit = False

class Mips16I8Instr(Mips16Instr):
    def __init__(self, name, funct, imm, instr_shift):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)
        verify_8bit_signed_value(imm, 'imm', instr_shift)

        shifted_imm = imm >> instr_shift

        # Instructions starting with 'b' are branch instructions and the assembler expects their
        # immediate argument to be odd to indicate a jump to a MIPS16 instruction. Branch 
        # instructions cannot jump to MIPS32 mode, so the bit is not part of the encoding.
        if name.startswith('b'):
            imm = imm | 0x01

        if 'nop' != name  or  0 != imm:
            self._args = (imm,)

        self._encoding = I8_op | (funct << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16I8sprelInstr(Mips16Instr):
    def __init__(self, name, funct, imm, instr_shift, sign_ext):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)

        if sign_ext:
            verify_8bit_signed_value(imm, 'imm', instr_shift)
        else:
            verify_8bit_unsigned_value(imm, 'imm', instr_shift)

        shifted_imm = imm >> instr_shift

        self._args = ('$sp', imm)
        self._encoding = I8_op | (funct << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16I8SwraSprelInstr(Mips16Instr):
    def __init__(self, name, funct, imm, instr_shift):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)
        verify_8bit_unsigned_value(imm, 'imm', instr_shift)

        shifted_imm = imm >> instr_shift

        self._args = ('$ra', str(imm) + '($sp)')
        self._encoding = I8_op | (funct << 8) | (shifted_imm & 0xFF)
        self._is32bit = False

class Mips16I8Movr32Instr(Mips16Instr):
    def __init__(self, name, funct, ry, r32):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)

        ry_num = MIPS16_REGS[ry]
        r32_num = MIPS32_REGS[r32]

        self._args = (ry, r32)
        self._encoding = I8_op | (funct << 8) | (ry_num << 5) | r32_num
        self._is32bit = False

class Mips16I8Mov32rInstr(Mips16Instr):
    def __init__(self, name, funct, r32, rz):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)

        r32_num = MIPS32_REGS[r32]
        rz_num = MIPS16_REGS[rz]

        # This instruction format swaps some bits of the r32 register, so get the bits.
        r32_2_0 = extract_bits(r32_num, 2, 0)
        r32_4_3 = extract_bits(r32_num, 4, 3)

        self._args = (r32, rz)
        self._encoding = I8_op | (funct << 8) | (r32_2_0 << 5) | (r32_4_3 << 3) | rz_num
        self._is32bit = False
        r32_num = MIPS32_REGS[r32]

class Mips16I8SvrsInstr(Mips16Instr):
    def __init__(self, name, s, ra, s0, s1, framesize):
        super().__init__(name)

        verify_flag_bit(s, 's')
        verify_flag_bit(ra, 'ra')
        verify_flag_bit(s0, 's0')
        verify_flag_bit(s1, 's1')

        # The framesize needs to be aligned to an 8-byte boundary becuase it's shifted down by 3
        # for the encoding. An encoding of zero means a framesize of 128.
        verify_integer_argument(framesize, 'framesize', 8, 128, 3)

        # This instruction has a weird argument format, so set them up manually.
        if ra != 0:
            self._args += ('$31',)
        if s0 != 0:
            self._args += ('$16',)
        if s1 != 0:
            self._args += ('$17',)

        self._args += (framesize,)

        framesize = (framesize >> 3) & 0x0F
        self._encoding = I8_op | SVRS_op | (s << 7) | (ra << 6) | (s0 << 5) | (s1 << 4) | framesize
        self._is32bit = False

class Mips16JalInstr(Mips16Instr):
    def __init__(self, name, x, imm, instr_shift):
        super().__init__(name)

        verify_flag_bit(x, 'x')
        
        max_26bit_value = (1<<26)-1
        verify_integer_argument(imm, 'imm', 0, max_26bit_value << instr_shift, instr_shift)

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_20_16 = extract_bits(shifted_imm, 20, 16)
        si_25_21 = extract_bits(shifted_imm, 25, 21)
        si_15_0 = shifted_imm & 0xFFFF

        self._args = (imm,)
        self._encoding = EXTJAL_op | (x << 26) | (si_20_16 << 21) | (si_25_21 << 16) | si_15_0
        self._is32bit = True

class Mips16ExtIInstr(Mips16Instr):
    def __init__(self, name, op, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        # This instruction swaps some bits of the immediate, so get the bits.
        # This was set up based on GNU Binutils test code in the source tree at
        # "gas/testsuite/gas/mips/save.s" because the MIPS16 datasheet is not that helpful.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        # This format is used only for branch instructions and the assembler expects the argument
        # to be odd to indicate that a jump to MIPS16 code is occurring. This does not appear to be
        # encoded in the instruction because it cannot jump to MIPS32.
        self._args = (imm | 0x01,)
        self._encoding = EXTEND_op | (si_10_5 << 21) | (si_15_11 << 16) | (op << 11) | si_4_0
        self._is32bit = True

class Mips16AsmacroInstr(Mips16Instr):
    def __init__(self, name, select, p4, p3, p2, p1, p0):
        super().__init__(name)

        verify_3bit_unsigned_value(select, 'select', 0)
        verify_3bit_unsigned_value(p4, 'p4', 0)
        verify_5bit_unsigned_value(p3, 'p3', 0)
        verify_3bit_unsigned_value(p2, 'p2', 0)
        verify_3bit_unsigned_value(p1, 'p1', 0)
        verify_5bit_unsigned_value(p0, 'p0', 0)

        self._args = (select, p0, p1, p2, p3, p4)
        self._encoding = (EXTRRR_op | (select << 24) | (p4 << 21) | (p3 << 16) | (p2 << 8) |
                            (p1 << 5) | p0)
        self._is32bit = True

class Mips16ExtRIInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        # Instructions starting with 'b' are branch instructions and the assembler expects their
        # immediate argument to be odd to indicate a jump to a MIPS16 instruction. Branch 
        # instructions cannot jump to MIPS32 mode, so the bit is not part of the encoding.
        if name.startswith('b'):
            imm = imm | 0x01

        self._args = (rx, imm)
        self._encoding = (EXTEND_op | (si_10_5 << 21) | (si_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | si_4_0)
        self._is32bit = True

class Mips16ExtRIpcrelInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', 0)

        rx_num = MIPS16_REGS[rx]

        # This instruction swaps some bits of the immediate, so get the bits.
        imm_10_5 = extract_bits(imm, 10, 5)
        imm_15_11 = extract_bits(imm, 15, 11)
        imm_4_0 = imm & 0x1F

        self._args = (rx, '$pc', imm)
        self._encoding = (EXTEND_op | (imm_10_5 << 21) | (imm_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | imm_4_0)
        self._is32bit = True

class Mips16ExtRIsprelInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        self._args = (rx, '$sp', imm)
        self._encoding = (EXTEND_op | (si_10_5 << 21) | (si_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | si_4_0)
        self._is32bit = True

class Mips16ExtRIpcrelMemInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        self._args = (rx, str(imm) + '($pc)')
        self._encoding = (EXTEND_op | (si_10_5 << 21) | (si_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | si_4_0)
        self._is32bit = True

class Mips16ExtRIsprelMemInstr(Mips16Instr):
    def __init__(self, name, op, rx, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        self._args = (rx, str(imm) + '($sp)')
        self._encoding = (EXTEND_op | (si_10_5 << 21) | (si_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | si_4_0)
        self._is32bit = True

class Mips16ExtRRIInstr(Mips16Instr):
    def __init__(self, name, op, rx, ry, imm, instr_shift):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        self._args = (ry, rx, imm)
        self._encoding = (EXTEND_op | (si_10_5 << 21) | (si_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | (ry_num << 5) | si_4_0)
        self._is32bit = True

class Mips16ExtRRIMemInstr(Mips16Instr):
    def __init__(self, name, op, rx, ry, imm):
        super().__init__(name)

        verify_opcode(op, 'op')
        verify_16bit_signed_value(imm, 'imm', 0)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        # This instruction swaps some bits of the immediate, so get the bits.
        imm_10_5 = extract_bits(imm, 10, 5)
        imm_15_11 = extract_bits(imm, 15, 11)
        imm_4_0 = imm & 0x1F

        # Memory instructions like "lw" and "sw" have a special format, so handle it here
        self._args = (ry, str(imm) + '(' + str(rx) + ')')
        self._encoding = (EXTEND_op | (imm_10_5 << 21) | (imm_15_11 << 16) | (op << 11) |
                            (rx_num << 8) | (ry_num << 5) | imm_4_0)
        self._is32bit = True

class Mips16ExtRRIAInstr(Mips16Instr):
    def __init__(self, name, rx, ry, f, imm):
        super().__init__(name)

        verify_15bit_signed_value(imm, 'imm', 0)
        verify_flag_bit(f, 'f')

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        # This instruction swaps some bits of the immediate, so get the bits.
        imm_10_4 = extract_bits(imm, 10, 4)
        imm_14_11 = extract_bits(imm, 14, 11)
        imm_3_0 = imm & 0x0F

        self._args = (ry, rx, imm)
        self._encoding = (EXTRRIA_op | (imm_10_4 << 20) | (imm_14_11 << 16) | 
                            (rx_num << 8) | (ry_num << 5) | (f << 4) | imm_3_0)
        self._is32bit = True

class Mips16ExtShiftInstr(Mips16Instr):
    def __init__(self, name, sa, rx, ry, f):
        super().__init__(name)

        verify_2bit_unsigned_value(f, 'f', 0)

        rx_num = MIPS16_REGS[rx]
        ry_num = MIPS16_REGS[ry]

        self._args = (ry, rx, sa)
        self._encoding = EXTSHIFT_op | (sa << 22) | (rx_num << 8) | (ry_num << 5) | f
        self._is32bit = True

class Mips16ExtI8Instr(Mips16Instr):
    def __init__(self, name, funct, imm, instr_shift):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        # Instructions starting with 'b' are branch instructions and the assembler expects their
        # immediate argument to be odd to indicate a jump to a MIPS16 instruction. Branch 
        # instructions cannot jump to MIPS32 mode, so the bit is not part of the encoding.
        if name.startswith('b'):
            imm = imm | 0x01

        self._args = (imm,)
        self._encoding = EXTI8_op | (si_10_5 << 21) | (si_15_11 << 16) | (funct << 8) | si_4_0
        self._is32bit = True

class Mips16ExtI8sprelInstr(Mips16Instr):
    def __init__(self, name, funct, imm, instr_shift):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)
        verify_16bit_signed_value(imm, 'imm', instr_shift)

        # This instruction swaps some bits of the immediate, so get the bits.
        shifted_imm = imm >> instr_shift
        si_10_5 = extract_bits(shifted_imm, 10, 5)
        si_15_11 = extract_bits(shifted_imm, 15, 11)
        si_4_0 = shifted_imm & 0x1F

        self._args = ('$sp', imm)
        self._encoding = EXTI8_op | (si_10_5 << 21) | (si_15_11 << 16) | (funct << 8) | si_4_0
        self._is32bit = True

class Mips16ExtI8SwraSprelInstr(Mips16Instr):
    def __init__(self, name, funct, imm):
        super().__init__(name)

        verify_3bit_unsigned_value(funct, 'funct', 0)

        # This instruction swaps some bits of the immediate, so get the bits.
        imm_10_5 = extract_bits(imm, 10, 5)
        imm_15_11 = extract_bits(imm, 15, 11)
        imm_4_0 = imm & 0x1F

        self._args = ('$ra', str(imm) + '($sp)')
        self._encoding = EXTI8_op | (imm_10_5 << 21) | (imm_15_11 << 16) | (funct << 8) | imm_4_0
        self._is32bit = True

class Mips16ExtI8SvrsInstr(Mips16Instr):
    def __init__(self, name, xsregs, aregs, s, ra, s0, s1, framesize):
        super().__init__(name)

        verify_3bit_unsigned_value(xsregs, 'xsregs', 0)
        verify_integer_argument(aregs, 'aregs', 0, 14, 0)  # 15 is reserved and should not be used
        verify_flag_bit(s, 's')
        verify_flag_bit(ra, 'ra')
        verify_flag_bit(s0, 's0')
        verify_flag_bit(s1, 's1')

        # The framesize needs to be aligned to an 8-byte boundary becuase it's shifted down by 3
        # for the encoding.
        verify_integer_argument(framesize, 'framesize', 0, 255 << 3, 3)

        # This instruction has a weird argument format, so set them up manually.
        # This was set up based on GNU Binutils test code in the source tree at
        # "gas/testsuite/gas/mips/save.s" because the MIPS16 datasheet is not that helpful.
        xs_args = ['$18', '$18-$19', '$18-$20', '$18-$21', '$18-$22', '$18-$23', '$18-$23, $31']
        if xsregs > 0:
            self._args += (xs_args[xsregs-1],)

        if ra != 0:
            self._args += ('$31',)
        if s0 != 0:
            self._args += ('$16',)
        if s1 != 0:
            self._args += ('$17',)

        # $a0-$a3 can be saved onto the caller's stack frame if they're used as arguments--in which
        # case they appear before the framesize--or as part of the callee's stack frame, in
        # in which they appear after the framesize and are called "static registers". Arguments do
        # not need to be restored, so this works a bit differently for SAVE and RESTORE instructions.
        aregs_args = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 0), (1, 1), (1, 2), (1, 3),
                      (2, 0), (2, 1), (2, 2), (0, 4), (3, 0), (3, 1), (4, 0)]
        if s != 0:
            num_arg_regs = aregs_args[aregs][0]
        else:
            num_arg_regs = 0
        
        if 4 == num_arg_regs:
            self._args += ('$4-$7',)
        elif 3 == num_arg_regs:
            self._args += ('$4-$6',)
        elif 2 == num_arg_regs:
            self._args += ('$4', '$5')
        elif 1 == num_arg_regs:
            self._args += ('$4',)

        self._args += (framesize,)

        num_static_regs = aregs_args[aregs][1]
        if 4 == num_static_regs:
            self._args += ('$4-$7',)
        elif 3 == num_static_regs:
            self._args += ('$5-$7',)
        elif 2 == num_static_regs:
            self._args += ('$6', '$7')
        elif 1 == num_static_regs:
            self._args += ('$7',)

        framesize = (framesize >> 3) & 0xFF
        fs_7_4 = extract_bits(framesize, 7, 4)
        fs_3_0 = extract_bits(framesize, 3, 0)

        self._encoding = (EXTI8_op | SVRS_op | (xsregs << 24) | (fs_7_4 << 20) | (aregs << 16) |
                            (s << 7) | (ra << 6) | (s0 << 5) | (s1 << 4) | fs_3_0)
        self._is32bit = True


if '__main__' == __name__:
    random.seed(0xDEADBEEF)   # used fixed seed so mulitple runs generate the same assembly

    mips16_instrs = [
        ##
        # Add immediate unsigned word
        # 2-operand
        Mips16RIInstr('addiu', 0b01001, rand_mips16_reg(), rand_imm(-128, -1), 0, True),
        Mips16RIInstr('addiu', 0b01001, rand_mips16_reg(), rand_imm(1, 127), 0, True),
        # 2-operand extended
        Mips16ExtRIInstr('addiu', 0b01001, rand_mips16_reg(), rand_imm(-32768, -1), 0),
        Mips16ExtRIInstr('addiu', 0b01001, rand_mips16_reg(), rand_imm(1, 32767), 0),
        # 3-operand
        Mips16RRIAInstr('addiu', rand_mips16_reg(), rand_mips16_reg(), 0, rand_imm(-8, -1)),
        Mips16RRIAInstr('addiu', rand_mips16_reg(), rand_mips16_reg(), 0, rand_imm(1, 7)),
        # 3-operand extended
        Mips16ExtRRIAInstr('addiu', rand_mips16_reg(), rand_mips16_reg(), 0, rand_imm(-16384, -1)),
        Mips16ExtRRIAInstr('addiu', rand_mips16_reg(), rand_mips16_reg(), 0, rand_imm(1, 16383)),
        # 3-operand PC-relative (the implicit PC counts as an operand)
        Mips16RIpcrelInstr('addiu', 0b00001, rand_mips16_reg(), rand_imm(4, 255, 4), 2),
        # 3-operand PC-realtive extended
        Mips16ExtRIpcrelInstr('addiu', 0b00001, rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRIpcrelInstr('addiu', 0b00001, rand_mips16_reg(), rand_imm(1, 32767)),
        # 2-operand SP-relative (the implicit SP counts as an operand)
        Mips16I8sprelInstr('addiu', 0b011, rand_imm(-128 << 3, -8, 8), 3, True),
        Mips16I8sprelInstr('addiu', 0b011, rand_imm(8, 127 << 3, 8), 3, True),
        # 2-operand SP-relative extended
        Mips16ExtI8sprelInstr('addiu', 0b011, rand_imm(-32768, -1), 0),
        Mips16ExtI8sprelInstr('addiu', 0b011, rand_imm(0, 32767), 0),
        # 3-operand SP-relative (the implicit SP counts as an operand)
        Mips16RIsprelInstr('addiu', 0b00000, rand_mips16_reg(), rand_imm(4, 255 << 2, 4), 2),
        # 3-operand SP-relative extended
        Mips16ExtRIsprelInstr('addiu', 0b00000, rand_mips16_reg(), rand_imm(-65536, -1), 0),
        Mips16ExtRIsprelInstr('addiu', 0b00000, rand_mips16_reg(), rand_imm(1, 65535), 0),

        ##
        # Add unsigned word 3-operand
        Mips16RRRInstr('addu', rand_mips16_reg(), rand_mips16_reg(), rand_mips16_reg(), 0b01),

        ##
        # And
        Mips16RRInstr('and', rand_mips16_reg(), rand_mips16_reg(), 0b01100),

        ##
        # Application-specific macro
        Mips16AsmacroInstr('asmacro', 4, 3, 21, 7, 6, 15),

        ##
        # Unconditional branch
        # 16-bit
        Mips16IInstr('b', 0b00010, rand_imm(-2048, -2, 2), 1),
        Mips16IInstr('b', 0b00010, rand_imm(2, 2046, 2), 1),
        # extended
        Mips16ExtIInstr('b', 0b00010, rand_imm(-65536, -2, 2), 1),
        Mips16ExtIInstr('b', 0b00010, rand_imm(2, 65534, 2), 1),

        ##
        # Branch on equal to zero
        # 16-bit
        Mips16RIInstr('beqz', 0b00100, rand_mips16_reg(), rand_imm(-256, -2, 2), 1, True),
        Mips16RIInstr('beqz', 0b00100, rand_mips16_reg(), rand_imm(2, 254, 2), 1, True),
        # extended
        Mips16ExtRIInstr('beqz', 0b00100, rand_mips16_reg(), rand_imm(-65536, -2, 2), 1),
        Mips16ExtRIInstr('beqz', 0b00100, rand_mips16_reg(), rand_imm(2, 65534, 2), 1),

        ##
        # Branch on not equal to zero
        # 16-bit
        Mips16RIInstr('bnez', 0b00101, rand_mips16_reg(), rand_imm(-256, -2, 2), 1, True),
        Mips16RIInstr('bnez', 0b00101, rand_mips16_reg(), rand_imm(2, 254, 2), 1, True),
        # extended
        Mips16ExtRIInstr('bnez', 0b00101, rand_mips16_reg(), rand_imm(-65536, -2, 2), 1),
        Mips16ExtRIInstr('bnez', 0b00101, rand_mips16_reg(), rand_imm(2, 65534, 2), 1),

        ##
        # Breakpoint
        Mips16RRbreakInstr('break', 0, 0b00101),

        ##
        # Branch on T equal to zero
        # 16-bit
        Mips16I8Instr('bteqz', 0b000, rand_imm(-256, -2, 2), 1),
        Mips16I8Instr('bteqz', 0b000, rand_imm(2, 254, 2), 1),
        # extended
        Mips16ExtI8Instr('bteqz', 0b000, rand_imm(-65536, -2, 2), 1),
        Mips16ExtI8Instr('bteqz', 0b000, rand_imm(2, 65534, 2), 1),

        ##
        # Branch on T not equal to zero
        # 16-bit
        Mips16I8Instr('btnez', 0b001, rand_imm(-256, -2, 2), 1),
        Mips16I8Instr('btnez', 0b001, rand_imm(2, 254, 2), 1),
        # extended
        Mips16ExtI8Instr('btnez', 0b001, rand_imm(-65536, -2, 2), 1),
        Mips16ExtI8Instr('btnez', 0b001, rand_imm(2, 65534, 2), 1),

        ##
        # Compare
        Mips16RRInstr('cmp', rand_mips16_reg(), rand_mips16_reg(), 0b01010),

        ##
        # Compare immediate
        # 16-bit
        Mips16RIInstr('cmpi', 0b01110, rand_mips16_reg(), rand_imm(0, 255), 0, False),
        # extended
        Mips16ExtRIInstr('cmpi', 0b01110, rand_mips16_reg(), rand_imm(0, 32767), 0),

        ##
        # Divide (signed)
        Mips16RRInstr('div', rand_mips16_reg(), rand_mips16_reg(), 0b11010),

        ##
        # Divide (unsigned)
        Mips16RRInstr('divu', rand_mips16_reg(), rand_mips16_reg(), 0b11011),

        ##
        # Jump and link
        Mips16JalInstr('jal', 0, rand_imm(4, (1<<28)-4, 4), 2),

        ##
        # Jump and link register
        Mips16RRjalrcInstr('jalr', rand_mips16_reg(), 0b010),

        ##
        # Jump and link register compact
        Mips16RRjalrcInstr('jalrc', rand_mips16_reg(), 0b110),

        ##
        # Jump and link exchange (MIPS16 format)
        Mips16JalInstr('jalx', 1, rand_imm(4, (1<<28)-4, 4), 2),

        ##
        # Jump register through ra
        Mips16RRjalrcraInstr('jr', 0b001),

        ##
        # Jump register through MIPS16 GPR
        Mips16RRjalrcInstr('jr', rand_mips16_reg(), 0b000),

        ##
        # Jump register through ra compact
        Mips16RRjalrcraInstr('jrc', 0b101),

        ##
        # Jump register through MIPS16 GPR compact
        Mips16RRjalrcInstr('jrc', rand_mips16_reg(), 0b100),

        ##
        # Load byte
        # 16-bit
        Mips16RRIMemInstr('lb', 0b10000, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 31), 0),
        # extended
        Mips16ExtRRIMemInstr('lb', 0b10000, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('lb', 0b10000, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Load byte unsigned
        # 16-bit
        Mips16RRIMemInstr('lbu', 0b10100, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 31), 0),
        # extended
        Mips16ExtRRIMemInstr('lbu', 0b10100, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('lbu', 0b10100, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Load halfword
        # 16-bit
        Mips16RRIMemInstr('lh', 0b10001, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 62, 2), 1),
        # extended
        Mips16ExtRRIMemInstr('lh', 0b10001, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('lh', 0b10001, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Load halfword unsigned
        # 16-bit
        Mips16RRIMemInstr('lhu', 0b10101, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 62, 2), 1),
        # extended
        Mips16ExtRRIMemInstr('lhu', 0b10101, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('lhu', 0b10101, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Load immediate
        # 16-bit
        Mips16RIInstr('li', 0b01101, rand_mips16_reg(), rand_imm(0, 255), 0, False),
        # extended
        Mips16ExtRIInstr('li', 0b01101, rand_mips16_reg(), rand_imm(0, 32767), 0),

        ##
        # Load word
        # 16-bit
        Mips16RRIMemInstr('lw', 0b10011, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 124, 4), 2),
        # extended
        Mips16ExtRRIMemInstr('lw', 0b10011, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('lw', 0b10011, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Load word PC-relative
        # 16-bit
        Mips16RIpcrelMemInstr('lw', 0b10110, rand_mips16_reg(), rand_imm(0, 1020, 4), 2),
        # extended
        Mips16ExtRIpcrelMemInstr('lw', 0b10110, rand_mips16_reg(), rand_imm(-32768, -1), 0),
        Mips16ExtRIpcrelMemInstr('lw', 0b10110, rand_mips16_reg(), rand_imm(1, 32767), 0),

        ##
        # Load word SP-relative
        # 16-bit
        Mips16RIsprelMemInstr('lw', 0b10010, rand_mips16_reg(), rand_imm(0, 1020, 4), 2),
        # extended
        Mips16ExtRIsprelMemInstr('lw', 0b10010, rand_mips16_reg(), rand_imm(-32768, -1), 0),
        Mips16ExtRIsprelMemInstr('lw', 0b10010, rand_mips16_reg(), rand_imm(1, 32767), 0),

        ##
        # Move from hi
        Mips16RRhiloInstr('mfhi', rand_mips16_reg(), 0b10000),

        ##
        # Move from lo
        Mips16RRhiloInstr('mflo', rand_mips16_reg(), 0b10010),

        ##
        # Move (16 to 32)
        Mips16I8Mov32rInstr('move', 0b101, rand_mips32_reg(), rand_mips16_reg()),

        ##
        # Move (32 to 16)
        Mips16I8Movr32Instr('move', 0b111, rand_mips16_reg(), rand_mips32_reg()),

        ##
        # Multiply word
        Mips16RRInstr('mult', rand_mips16_reg(), rand_mips16_reg(), 0b11000),

        ##
        # Multiply word unsigned
        Mips16RRInstr('multu', rand_mips16_reg(), rand_mips16_reg(), 0b11001),

        ##
        # Negate
        Mips16RRInstr('neg', rand_mips16_reg(), rand_mips16_reg(), 0b01011),

        ##
        # No operation
        Mips16I8Instr('nop', 0b101, 0, 0),

        ##
        # Not
        Mips16RRInstr('not', rand_mips16_reg(), rand_mips16_reg(), 0b01111),

        ##
        # Or
        Mips16RRInstr('or', rand_mips16_reg(), rand_mips16_reg(), 0b01101),

        ##
        # Restore
        # 16-bit
        Mips16I8SvrsInstr('restore', 0, 0, 0, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 0, 0, 1, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 0, 1, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 0, 1, 1, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 1, 0, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 1, 0, 1, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 1, 1, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('restore', 0, 1, 1, 1, rand_imm(8, 128, 8)),
        # extended
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 0, 0, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 0, 0, 1, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 0, 1, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 0, 1, 1, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 1, 0, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 1, 0, 1, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 1, 1, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('restore', rand_imm(0, 7), rand_imm(0, 14), 0, 1, 1, 1, rand_imm(0, 2040, 8)),

        ##
        # Save
        # 16-bit
        Mips16I8SvrsInstr('save', 1, 0, 0, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 0, 0, 1, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 0, 1, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 0, 1, 1, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 1, 0, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 1, 0, 1, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 1, 1, 0, rand_imm(8, 128, 8)),
        Mips16I8SvrsInstr('save', 1, 1, 1, 1, rand_imm(8, 128, 8)),
        # extended
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 0, 0, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 0, 0, 1, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 0, 1, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 0, 1, 1, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 1, 0, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 1, 0, 1, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 1, 1, 0, rand_imm(0, 2040, 8)),
        Mips16ExtI8SvrsInstr('save', rand_imm(0, 7), rand_imm(0, 14), 1, 1, 1, 1, rand_imm(0, 2040, 8)),

        ##
        # Store byte
        # 16-bit
        Mips16RRIMemInstr('sb', 0b11000, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 31), 0),
        # extended
        Mips16ExtRRIMemInstr('sb', 0b11000, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('sb', 0b11000, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Software debug breakpoint
        Mips16RRbreakInstr('sdbbp', 0, 0b00001),

        ##
        # Sign-extend byte
        Mips16RRcnvtInstr('seb', rand_mips16_reg(), 0b100),

        ##
        # Sign-extend halfword
        Mips16RRcnvtInstr('seh', rand_mips16_reg(), 0b101),

        ##
        # Store halfword
        # 16-bit
        Mips16RRIMemInstr('sh', 0b11001, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 62, 2), 1),
        # extended
        Mips16ExtRRIMemInstr('sh', 0b11001, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('sh', 0b11001, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Shift word left logical
        # 16-bit
        Mips16ShiftInstr('sll', rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 8), 0b00),
        # extended
        Mips16ExtShiftInstr('sll', rand_imm(0, 31), rand_mips16_reg(), rand_mips16_reg(), 0b00),

        ##
        # Shift word left logical variable
        Mips16RRInstr('sllv', rand_mips16_reg(), rand_mips16_reg(), 0b00100),

        ##
        # Set on less than
        Mips16RRInstr('slt', rand_mips16_reg(), rand_mips16_reg(), 0b00010),

        ##
        # Set on less than immediate
        # 16-bit
        Mips16RIInstr('slti', 0b01010, rand_mips16_reg(), rand_imm(0, 255), 0, False),
        # extended
        Mips16ExtRIInstr('slti', 0b01010, rand_mips16_reg(), rand_imm(-32768, -1), 0),
        Mips16ExtRIInstr('slti', 0b01010, rand_mips16_reg(), rand_imm(1, 32767), 0),

        ##
        # Set on less than immediate unsigned
        # 16-bit
        Mips16RIInstr('sltiu', 0b01011, rand_mips16_reg(), rand_imm(0, 255), 0, False),
        # extended
        Mips16ExtRIInstr('sltiu', 0b01011, rand_mips16_reg(), rand_imm(-32768, -1), 0),
        Mips16ExtRIInstr('sltiu', 0b01011, rand_mips16_reg(), rand_imm(1, 32767), 0),

        ##
        # Set on less than unsigned
        Mips16RRInstr('sltu', rand_mips16_reg(), rand_mips16_reg(), 0b00011),

        ##
        # Shift word right arithmetic
        # 16-bit
        Mips16ShiftInstr('sra', rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 8), 0b11),
        # extended
        Mips16ExtShiftInstr('sra', rand_imm(0, 31), rand_mips16_reg(), rand_mips16_reg(), 0b11),

        ##
        # Shift word right arithmetic variable
        Mips16RRInstr('srav', rand_mips16_reg(), rand_mips16_reg(), 0b00111),

        ##
        # Shift word right logical
        # 16-bit
        Mips16ShiftInstr('srl', rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 8), 0b10),
        # extended
        Mips16ExtShiftInstr('srl', rand_imm(0, 31), rand_mips16_reg(), rand_mips16_reg(), 0b10),

        ##
        # Shift word right logical variable
        Mips16RRInstr('srlv', rand_mips16_reg(), rand_mips16_reg(), 0b00110),

        ##
        # Subtract unsigned word
        Mips16RRRInstr('subu', rand_mips16_reg(), rand_mips16_reg(), rand_mips16_reg(), 0b11),

        ##
        # Store word
        # 16-bit
        Mips16RRIMemInstr('sw', 0b11011, rand_mips16_reg(), rand_mips16_reg(), rand_imm(0, 124, 4), 2),
        # extended
        Mips16ExtRRIMemInstr('sw', 0b11011, rand_mips16_reg(), rand_mips16_reg(), rand_imm(-32768, -1)),
        Mips16ExtRRIMemInstr('sw', 0b11011, rand_mips16_reg(), rand_mips16_reg(), rand_imm(1, 32767)),

        ##
        # Store word SP-relative
        # 16-bit
        Mips16RIsprelMemInstr('sw', 0b11010, rand_mips16_reg(), rand_imm(0, 1020, 4), 2),
        # extended
        Mips16ExtRIsprelMemInstr('sw', 0b11010, rand_mips16_reg(), rand_imm(-32768, -1), 0),
        Mips16ExtRIsprelMemInstr('sw', 0b11010, rand_mips16_reg(), rand_imm(1, 32767), 0),

        ##
        # Store word in register RA, SP-relative
        # 16-bit
        Mips16I8SwraSprelInstr('sw', 0b010, rand_imm(4, 1020, 4), 2),
        # extended
        Mips16ExtI8SwraSprelInstr('sw', 0b010, rand_imm(-32768, -1)),
        Mips16ExtI8SwraSprelInstr('sw', 0b010, rand_imm(1, 32767)),

        ##
        # Exclusive or
        Mips16RRInstr('xor', rand_mips16_reg(), rand_mips16_reg(), 0b01110),

        ##
        # Zero-extend byte
        Mips16RRcnvtInstr('zeb', rand_mips16_reg(), 0b000),

        ##
        # Zero-extend halfword
        Mips16RRcnvtInstr('zeh', rand_mips16_reg(), 0b001),
    ]

    print('# REQUIRES: mips-registered-target')
    print('# RUN: llvm-mc -arch=mipsel -mcpu=mips32r2 -mattr=+mips16 -show-encoding -show-inst %%s | FileCheck %%s')
    print()

    for instr in mips16_instrs:
        instr_str = instr.get_instr_string()

        instr_line = instr_str

        if len(instr_line) < 32:
            instr_line += ' ' * (32 - len(instr_line))
        else:
            instr_line += '  '
        
        instr_line += '# CHECK: ' + instr_str

        if len(instr_line) < 72:
            instr_line += ' ' * (72 - len(instr_line))
        else:
            instr_line += '  '
        
        instr_encoding = instr.get_encoding_as_bytes('little')
        instr_line += '# encoding: [' + ','.join([hex(e) for e in instr_encoding]) + ']'

        print(instr_line)
