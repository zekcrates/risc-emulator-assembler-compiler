#!/usr/bin/env python3
from enum import Enum
import os
import struct
import glob
import binascii
from elftools.elf.elffile import ELFFile


regnames = \
  ['x0', 'ra', 'sp', 'gp', 'tp'] + ['t%d'%i for i in range(0,3)] + ['s0', 's1'] +\
  ['a%d'%i for i in range(0,8)] +\
  ['s%d'%i for i in range(2,12)] +\
  ['t%d'%i for i in range(3,7)] + ["PC"]
PC = 32

class RegisterFile:
    def __init__(self):
        self.registers = [0] * 33 
    
    def __getitem__(self,key):
        return self.registers[key]

    def __setitem__(self,key,value):
        if key ==0 :
            return 
        self.registers[key] = value & 0xFFFFFFFF



regfile =RegisterFile()
regfile[PC] = 0x80000000 
memory = b'\x00'*0x4000 



class Ops(Enum):
  LUI = 0b0110111    # load upper immediate
  LOAD = 0b0000011
  STORE = 0b0100011

  AUIPC = 0b0010111  # add upper immediate to pc
  BRANCH = 0b1100011
  JAL = 0b1101111
  JALR = 0b1100111

  IMM = 0b0010011
  OP = 0b0110011

  MISC = 0b0001111
  SYSTEM = 0b1110011

class Funct3(Enum):
  ADD = SUB = ADDI = 0b000
  SLLI = 0b001
  SLT = SLTI = 0b010
  SLTU = SLTIU = 0b011

  XOR = XORI = 0b100
  SRL = SRLI = SRA = SRAI = 0b101
  OR = ORI = 0b110
  AND = ANDI = 0b111

  BEQ = 0b000
  BNE = 0b001
  BLT = 0b100
  BGE = 0b101
  BLTU = 0b110
  BGEU = 0b111

  LB = SB = 0b000
  LH = SH = 0b001
  LW = SW = 0b010
  LBU = 0b100
  LHU = 0b101

  ECALL = 0b000
  CSRRW = 0b001
  CSRRS = 0b010
  CSRRC = 0b011
  CSRRWI = 0b101
  CSRRSI = 0b110
  CSRRCI = 0b111


def reset():
    pass 

def ws(addr,data):
    global memory
  

    addr -= 0x80000000
    print("addr :", addr)
    if addr <0 or addr > len(memory):
        raise Exception("Address is invalid")
    
    memory = memory[:addr] + data + memory[addr+len(data): ]
    # print(memory)

# ws(0x80000008, struct.pack('B', 0b011010)) 


def read_32_bits(addr):
    addr -= 0x80000000
    if addr <0 or addr > len(memory):
        print("Address is not valid")
        
    res =  struct.unpack("<I", memory[addr: addr+4])
    out = res[0]
    print(out)
    return out 

def dump():
  pp = []
  for i in range(33):
    if i != 0 and i % 8 == 0:
      pp += "\n"
    pp += " %3s: %08x" % (regnames[i], regfile[i])
  print(''.join(pp))
def getbits(instruction, high,low):
    # first move the instruction to the end 
    # mask the s..end 
    move = (instruction >> low)
    
    width =(high-low)+ 1 #(3-0) is 3 but should be 4 bits so +1 
    mask = (1<< width) -1

    ans = move & mask 
    # print(f"ans: {ans:32b}")

    return ans 

def arith(func,x1,x2, other):
    if func == Funct3.ADDI:
        if other:
            return x1-x2
        else: 
            return x1+x2 
    # xori 
    elif func == Funct3.XOR:
      return x1 ^ x2
    #ori 
    elif func == Funct3.ORI:
        return x1 | x2 
    # andi 
    elif func == Funct3.ANDI:
        return x1 & x2 
    # slli 
    elif func== Funct3.SLLI:
        return (x1<< (x2&0x1f))

    # srli 
    # srai 

    elif func== Funct3.SRLI:
        if other: #srai
            sb = x1 >> 31
            out = x1 >> (x2&0x1f)
            out |= (0xFFFFFFFF * sb) << (32-(x2&0x1f))
            return out
        else: 
            return (x1 >> (x2 & 0x1f))

    # slti 
    elif func == Funct3.SLT:
        return int(sign_extend(x1, 32) < sign_extend(x2,32))
    
    # sltiu 
    elif func == Funct3.SLTU:
        return int((x1& 0xFFFFFFFF) < (x2& 0xFFFFFFFF))
    else :
        raise Exception("write arith funct3 %r" % func) 

def conditional(func, vs1, vs2):
    if func == Funct3.BLTU:
        return vs1 < vs2
    elif func == Funct3.BGEU:
        return vs1 >= vs2
        
    elif func == Funct3.BLT:
        return sign_extend(vs1, 32) < sign_extend(vs2, 32)
    elif func == Funct3.BGE:
        return sign_extend(vs1, 32) >= sign_extend(vs2, 32)
        
    elif func == Funct3.BEQ:
        return vs1 == vs2
    elif func == Funct3.BNE:
        return vs1 != vs2
    return False
def sign_extend(x,leng):
    # (1000) >> (3) we get (0001) which == 1 
   if x >> (leng-1) == 1:
        # (1<<4) -> 2^4 -> 16 -> (16-8) = 8 -> -8
        return -((1<< leng) - x)
   else:
      return x 
def step(): 
    # pc gives us the next addr to work 
    # we need to get the addr: addr+4 bits from the memory 

    #Decode
    # instruction = read_32_bits(regfile[PC])
    #ADD x3, x1, x2 0x002081B3

    #ADDI x3, x1, -5
    instruction = 0xFFB08193
    print(instruction)

    opcode = getbits(instruction, 6,0)
    opcode = Ops(opcode)

    is_load = opcode == Ops.LOAD
    is_store = opcode == Ops.STORE


    funct3 = getbits(instruction,14,12)
    funct3 = Funct3(funct3)


    rd= getbits(instruction, 11,7)
    rs1 = getbits(instruction, 19, 15)
    rs2 = getbits(instruction, 24, 20)

    # For I type
    imm_i = getbits(instruction,31,20)
    imm_i = sign_extend(imm_i, 12)

    # For U type
    imm_u = getbits(instruction,31,12)
    imm_u = sign_extend(imm_u << 12 ,32)
    

    # For B type 
    bit_12   = getbits(instruction, 32, 31)
    bits_10_5 = getbits(instruction, 30, 25)
    bits_4_1  = getbits(instruction, 11, 8)
    bit_11   = getbits(instruction, 8, 7)

    imm_b = (bit_12 << 12) | (bit_11 << 11) | (bits_10_5 << 5) | (bits_4_1 << 1)
    imm_b = sign_extend(imm_b, 13)


    # For J type

    imm_j = sign_extend((getbits(instruction, 32, 31)<<20) | (getbits(instruction, 30, 21)<<1) | (getbits(instruction,21, 20)<<11) | (getbits(instruction, 19, 12)<<12), 21)




    # For S type 
    imm_s = sign_extend((getbits(instruction,31,25) << 5) | (getbits(instruction,11,7)), 12)



    regfile[rs1] = 10 
    rs1 = regfile[rs1]
    rs2 = regfile[rs2]
    current_pc = regfile[PC]


    imm = {Ops.OP:rs2 , Ops.IMM: imm_i, Ops.LUI: imm_u, Ops.AUIPC: imm_u, Ops.AUIPC: imm_u,
           Ops.BRANCH: imm_b, Ops.JAL: imm_j , Ops.JALR: imm_i, Ops.STORE: imm_s}[opcode]
    should_writeback_to_register  = opcode in [Ops.OP , Ops.IMM, Ops.AUIPC, Ops.LUI, Ops.JAL, Ops.JALR]

    funct3 = funct3 if opcode in [Ops.OP,Ops.IMM ] else Funct3.ADD
    funct7 = getbits(instruction,31,25)

    other = (funct7==0b0100000) and ((opcode == Ops.OP) or (opcode == Ops.IMM and funct3 == Funct3.SRAI))
    left = current_pc if opcode in [Ops.AUIPC, Ops.BRANCH] else ( 0 if opcode == Ops.LUI else rs1) 
    take_branch = opcode in [Ops.JAL, Ops.JALR] or (opcode== Ops.BRANCH and conditional(funct3, rs1,imm))
    
    result = arith(funct3,left,imm, other)

    if is_load:
        if funct3 == Funct3.LB:
            result = sign_extend(read_32_bits(result) &0xFF , 8)

        elif funct3 == Funct3.LH:
            result = sign_extend(read_32_bits(result)&0XFFFF, 16)
        elif funct3 == Funct3.LW:
            result = read_32_bits(result)
        elif funct3== Funct3.LBU:
            result = read_32_bits(result)&0xFF
        elif funct3== Funct3.LHU:
            result = read_32_bits(result)& 0xFFFF

    elif is_store:
        # store byte 
        if funct3== Funct3.SB:
            # write last byte in result(which is the memory address)
            ws(result, struct.pack('B',rs2&0xFF))
        # store half 
        elif funct3 == Funct3.SH:
            ws(result, struct.pack('H', rs2& 0xFFFF))
        # store word 
        elif funct3 == Funct3.SW:
            ws(result , struct.pack('I'),rs2)
        
    
    if take_branch:
        # refer: https://www.cs.sfu.ca/~ashriram/Courses/CS295/assets/notebooks/RISCV/RISCV_CARD.
        # pc will have the result instead of +4 
        if should_writeback_to_register:
            regfile[rd] = current_pc+ 4 
        regfile[PC] = result 
    else:
        if should_writeback_to_register:
            regfile[rd] = result 
        regfile[PC] = current_pc + 4 
         
    # dump()

step()
