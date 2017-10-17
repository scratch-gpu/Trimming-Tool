#! /usr/bin/env python

#Copyright (c) 2014, Vertical Research Group, University of Wisconsin-Madison
#Copyright (c) 2017  IT - Coimbra, Universidade de Coimbra and INESC-ID,
#Universidade de Lisboa
#
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#
#1. Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
#3. Neither the name of the copyright holder nor the names of its contributors
#   may be used to endorse or promote products derived from this software
#   without specific prior written permission.
#
#4. The use of this tool in research works and publications, assumes that
#   the following articles are cited:
#
#SCRATCH Framework (MIAOW 2.0):
# - P. Duarte, P. Tomás, G. Falcao. SCRATCH: A Soft-GPU Architecture and
#   Trimming Tool for Application-Specific Contexts. In IEEE/ACM
#   International Symposium on Microarchitecture (MICRO), Oct. 2017, pp 1-12.
#
#Original MIAOW:
# - Balasubramanian R, Gangadhar V, Guo Z, Ho CH, Joseph C, Menon J, Drumond MP,
#   Paul R, Prasad S, Valathol P, Sankaralingam K. Enabling gpgpu low-level
#   hardware explorations with miaow: An Open-Source RTL Implementation of a GPGPU.
#   ACM Transactions on Architecture and Code Optimization (TACO), Jul. 2015,
#   vol. 12, no. 2, pp. 21.
#   
#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
#ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
#FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
#DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
#CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
#OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import csv
import sys

class app_proc():

    def __init__(self,csv_file):
        self.csv_file  = csv_file
        self.type_bits = {
            "VOPC" : "0111110"  ,
            "VOP1" : "0111111"  ,
            "VOP2" : "0"        ,
            "SOPP" : "101111111",
            "SOPC" : "101111110",
            "SOP1" : "10111110" ,
            "SOPK" : "1011"     ,
            "SOP2" : "10"       ,
            "SMRD" : "11000"    ,
            "VOP3a": "110100"   ,
            "MTBUF": "111010"   }

    def get_type_format_bits(self,i_type):
        # Returns the encoding bits for the given type
        assert i_type in self.type_bits, "Type {} not supported".format(i_type)
        return self.type_bits[i_type]

    def get_instruction_type(self,inst_b,warning_print=False):
        # Given an instruction opcode (either 32 char binary string or integer) returns the instruction type
        bitstring = "{0:032b}".format(inst_b) if isinstance(inst_b,int) else inst_b
        i_type    = ""
        opcode    = ""

        if bitstring[0] == "0":
            if   bitstring[1:7] == "111110":
                i_type = "VOPC"
                opcode = bitstring[7:15]
            elif bitstring[1:7] == "111111":
                i_type = "VOP1"
                opcode = bitstring[15:23]
            else:
                i_type = "VOP2"
                opcode = bitstring[1:7]

        elif bitstring[:2] == "10":
            #Scalar type
            if   bitstring[2:9] == "1111111":
                i_type = "SOPP"
                opcode = bitstring[9:16]
            elif bitstring[2:9] == "1111110":
                i_type = "SOPC"
                opcode = bitstring[9:16]
            elif bitstring[2:8] == "111110":
                i_type = "SOP1"
                opcode = bitstring[15:23]
            elif bitstring[2:4] == "11":
                i_type = "SOPK"
                opcode = bitstring[4:9]
            else:
                i_type = "SOP2"
                opcode = bitstring[2:9]

        elif bitstring[:5] == "11000":
                i_type = "SMRD"
                opcode = bitstring[5:10]

        elif bitstring[:6] == "111010":
                i_type = "MTBUF"
                opcode = bitstring[13:16]

        elif bitstring[:6] == "110100":
                i_type = "VOP3A"
                opcode = bitstring[6:15]

        if i_type == "" and warning_print:
            sys.stderr.write("WARNING: No support for instruction with bitstring: {}. Instruction will be ignored.\n\r".format(bitstring))

        return i_type,opcode

    def get_instruction_fu(self,inst,fu,i_type):
        #Given an instruction name, the functional unit selected by CodeXL and
        #the instruction type returns the hardware functional unit that the instruction uses
        hw_fu = ""
        
        S1 = set(inst.split('_'))
        S2 = set(["F32","F64","F16"])

        is_float = S1.intersection(S2)


        if fu == "Scalar" or fu == "Branch" or fu == "Flow Control":
            if i_type == "SMRD":
                hw_fu = "LSU"
            else:
                hw_fu = "SALU"
        elif fu == "Vector Memory":
            hw_fu = "LSU"
        elif is_float:
            hw_fu = "SIMF"
        else:
            hw_fu = "SIMD"

        return hw_fu

    def get_instructions(self):
        # Reads a csv file created by CodeXL
        # For each non-empty line obtains the instruction, its type and its hardware F.U.
        # Creates a dictionary whose keys are the hardware F.U. used and the
        #entry is a list of tuples, each containing an instruction, the corresponding instruction type and the opcode.
        # Creates a list of used types
        req_inst  = {}
        type_list = []
        with open(self.csv_file,'r') as f:
            inst_file = csv.reader(f)
            inst_file.next() #jump title line
            for row in inst_file:
                row = [r for r in row if r!='']
                if len(row) < 6:
                    continue
                #Retrieve row values
                inst   = row[1]
                fu     = row[4]
                inst_b = [int(val,16) for val in row[5].split(' ')]
                #Process row values
                i_type,opcode = self.get_instruction_type(inst_b[0],warning_print=True)
                if i_type != "":
                    hw_fu  = self.get_instruction_fu  (inst,fu,i_type)
                    
                    n_inst = tuple([inst,i_type,opcode])
    
                    if hw_fu not in req_inst:
                        req_inst[hw_fu] = []
    
                    if n_inst not in req_inst[hw_fu]:
                        req_inst[hw_fu].append(n_inst)
                        if i_type not in type_list:
                            type_list.append(i_type)
    
        return req_inst,type_list

