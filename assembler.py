import re
import struct
from cpu import Ops, Funct3
import os 
import sys 

regnames = [
    'x0', 'ra', 'sp', 'gp', 'tp'] + \
    ['t%d'%i for i in range(0,3)] + \
    ['s0', 's1'] + \
    ['a%d'%i for i in range(0,8)] + \
    ['s%d'%i for i in range(2,12)] + \
    ['t%d'%i for i in range(3,7)] + ["PC"]
regmap = {name: idx for idx, name in enumerate(regnames)}
for i in range(0, 32):
    regmap[f"x{i}"] = i

# print(regmap)

R_TYPE = {
    "ADD": {"funct7": 0b0000000, "funct3": 0b000},
    "SUB": {"funct7": 0b0100000, "funct3": 0b000},
    "XOR": {"funct7": 0b0000000, "funct3": 0b100},
    "OR":  {"funct7": 0b0000000, "funct3": 0b110},
    "AND": {"funct7": 0b0000000, "funct3": 0b111},
    "SLL": {"funct7": 0b0000000, "funct3": 0b001},
    "SRL": {"funct7": 0b0000000, "funct3": 0b101},
    "SRA": {"funct7": 0b0100000, "funct3": 0b101},
    "SLT": {"funct7": 0b0000000, "funct3": 0b010},
    "SLTU": {"funct7": 0b0000000, "funct3": 0b011},
}


I_TYPE = {
    "ADDI": {"funct3": 0b000, "opcode": 0b0010011}, 
    "XORI": {"funct3": 0b100, "opcode": 0b0010011},
    "ORI": {"funct3": 0b110, "opcode": 0b0010011},
    "ANDI": {"funct3": 0b111, "opcode": 0b0010011},
    "ANDI": {"funct3": 0b111, "opcode": 0b0010011},
    "SLTI": {"funct3": 0b010, "opcode": 0b0010011}, 
    "SLTIU": {"funct3": 0b011, "opcode": 0b0010011}, 

    "LB": {"funct3": 0b000, "opcode": 0b0000011},
    "LH": {"funct3": 0b001, "opcode": 0b0000011},
    "LW": {"funct3": 0b010, "opcode": 0b0000011},
    "LBU": {"funct3": 0b100, "opcode": 0b0000011},
    "LHU": {"funct3": 0b101, "opcode": 0b0000011},

    "SLLI": {"funct3": 0b001, "funct7": 0b0000000, "opcode": 0b0010011},
    "SRLI": {"funct3": 0b101, "funct7": 0b0000000, "opcode": 0b0010011},
    "SRAI": {"funct3": 0b101, "funct7": 0b0100000, "opcode": 0b0010011},
     
}

S_TYPE = {
    "SB": {"funct3": 0b000, "opcode": Ops.STORE.value},
    "SH": {"funct3": 0b001, "opcode": Ops.STORE.value},
    "SW": {"funct3": 0b010, "opcode": Ops.STORE.value},
}

B_TYPE=  {
    "BEQ": {"funct3" : 0b000, "opcode": Ops.BRANCH.value}, 
    "BNE": {"funct3" : 0b001, "opcode": Ops.BRANCH.value}, 
    "BLT": {"funct3" : 0b100, "opcode": Ops.BRANCH.value}, 
    "BGE": {"funct3" : 0b101, "opcode": Ops.BRANCH.value}, 
    "BLTU": {"funct3" : 0b110, "opcode": Ops.BRANCH.value}, 
    "BGEU": {"funct3" : 0b111, "opcode": Ops.BRANCH.value}, 
}


U_TYPE = {
    "LUI" : {"opcode": 0b0110111},
    "AUIPC": {"opcode": 0b0010111}
}


J_TYPE = {
    "JAL": {"opcode": Ops.JAL.value}
}




def read_line(line):
    # ignore the comments 
    if line.startswith('//') or line.startswith('#'):
        return 
    tokens = re.split(r"[ ,]+", line)
    instr = tokens[0].upper()

    if instr in R_TYPE:
        rd    = regmap[tokens[1]] & 0x1F
        rs1   = regmap[tokens[2]] & 0x1F
        rs2   = regmap[tokens[3]] & 0x1F
        opcode = Ops.OP.value & 0x7F

        funct3 = R_TYPE[instr]["funct3"]
        funct7 = R_TYPE[instr]["funct7"]

        instruction = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

        print(f"32-bit instruction: 0b{instruction:032b}")
        print(f"32-bit instruction hex: 0x{instruction:08X}")

    elif instr in S_TYPE:
        # ['SB', 'x5', '8(x2)']

        rs1   = regmap[tokens[1]] & 0x1F
        offset_base = tokens[2]
        offset_str, base_str = offset_base.replace(')', '').split('(')

        # 12 bit imm
        imm = int(offset_str)& 0xFFF
        rs2 = regmap[base_str] & 0x1F
        
        funct3 = S_TYPE[instr]["funct3"]
        opcode = S_TYPE[instr]["opcode"]
        
        instruction = ((imm >> 5 ) << 25) | (rs2 << 20 ) | (rs1 << 15) | (funct3 << 12) | ((imm & 0x1F) << 7) | opcode 

        # no rd and  funct7 but we have imm 


    elif instr in B_TYPE:

        #BEQ x1, x2, 16

        rs1 = regmap[tokens[1]] & 0x1F 
        rs2 = regmap[tokens[2]] & 0x1F 

        imm = int(tokens[3])& 0x1FFF # get 13 bits 
        bit12 =   (imm>> 12 ) & 0x1 
        bit_10_5  = (imm>> 5) & 0x3F # get 6 bits 
        bit_4_1 = (imm>> 1 ) & 0xF 
        bit_11 = (imm>> 11) & 0x1 

        funct3 = B_TYPE[instr]["funct3"]
        opcode = B_TYPE[instr]["opcode"]


        instruction = (bit12 << 31)| (bit_10_5 << 25 ) | (rs2 << 20) | (rs1 << 15 ) | (funct3 << 12)| (bit_4_1 << 8 ) | (bit_11 << 7) | opcode 


    elif instr in J_TYPE:
        # JAL x1, 32
 
        rd    = regmap[tokens[1]] & 0x1F
        imm = int(tokens[2]) & 0x1FFFFF # get 21 bits 

        bit_20 = (imm >> 20) & 0x1 
        bit_10_1 = (imm>> 1 ) & 0x3FF
        bit_11 = (imm>>11) & 0x1 
        opcode = J_TYPE[instr]["opcode"]
        bits_19_12 = (imm>>  12) & 0xFF 

        instruction = (bit_20 << 31) | (bit_10_1 << 21)  | (bit_11 << 20) | (bits_19_12 << 12 ) |(rd << 7) | opcode 

    elif instr in U_TYPE:
        # LUI x5, 0x12345  
        rd = regmap[tokens[1]] & 0x1F 
        imm = int(tokens[2]) & 0xFFFFF # take 20 bits 

        instruction = (imm << 12) | (rd << 7 ) | opcode 

    elif instr in I_TYPE:
        if instr in ["SLLI", "SRLI", "SRAI"]:
            # shamt 
            shamt = int(tokens[3]) & 0x1F   # 5 bits only
            rd = regmap[tokens[1]] & 0x1F
            rs1 = regmap[tokens[2]] & 0x1F
            funct3 = I_TYPE[instr]["funct3"]
            funct7 = I_TYPE[instr]["funct7"]
            opcode = I_TYPE[instr]["opcode"]

            instruction = (funct7 << 25) | (shamt << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode

        else:
            rd = regmap[tokens[1]] & 0x1F
            rs1 = regmap[tokens[2]] & 0x1F 
            imm = int(tokens[3]) & 0xFFF 
            funct3 = I_TYPE[instr]["funct3"]
            opcode = I_TYPE[instr]["opcode"]
            instruction = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode



    return instruction




if __name__ == '__main__':
    # read a file of type .s or anything 

    if len(sys.argv)  < 2 :
        print("Usage: python main.py filename.s")
        
    # for each line in file 
    # convert to binary
    filename = sys.argv[1]

    tokens = filename.split('.')
    # print(tokens)

    assert tokens[1] == 's' , "File should be .s type"    
    
    output_filename = filename.replace('.s', '.bin')
    instructions = []
    # line = "ADD x3,x1,x2"    
    # read_line(line)

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            inst = read_line(line)
            if inst is not None:
                instructions.append(inst)
    with open(output_filename, 'w') as out:
        for inst in instructions:
            out.write(f"{inst:032b}\n")
    # create a file of type .o or anything 

    # write binary to new file.o 
    
