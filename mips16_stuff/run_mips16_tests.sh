#!/usr/bin/env bash

LLVM_BIN_DIR=../pic32clang/build/llvm/bin/
MIPS16_OPTS='-arch=mipsel -mcpu=mips32r2 -mattr=+mips16'

# Change to this script's location just so we have a known baseline.
cd "${0%/*}"

# Make the temp file here so we can look at it easily if something goes wrong.
temp_file=./mips16_temp.txt
rm -f ${temp_file}
echo "Temp file created at ${temp_file}."

##
# TEST 1
#
echo "----------"
echo "Checking that we recognize valid MIPS16 instructions."

test_file=./valid_insns.s
if ! ${LLVM_BIN_DIR}llvm-mc ${MIPS16_OPTS} -show-encoding -show-inst ${test_file} > ${temp_file} ; then
    echo "llvm_mc FAILED"
    exit 1
fi

if ! ${LLVM_BIN_DIR}FileCheck ${test_file} < ${temp_file} ; then
    echo "FileCheck FAILED"
    exit 2
fi

echo "SUCCESS! We recognize valid MIPS16 instructions!"

##
# TEST 2
#
echo "----------"
echo "Checking that we reject invalid MIPS16 instructions."

test_file=./invalid_insns.s
if ! ${LLVM_BIN_DIR}not ${LLVM_BIN_DIR}llvm-mc ${MIPS16_OPTS} ${test_file} 2> ${temp_file} ; then
    echo "llvm_mc FAILED"
    exit 3
fi

if ! ${LLVM_BIN_DIR}FileCheck ${test_file} < ${temp_file} ; then
    echo "FileCheck FAILED"
    exit 4
fi

echo "SUCCESS! We properly handle invalid MIPS16 instructions!"

##
# TEST 3
#
echo "----------"
echo "Checking that we can decode data back into valid MIPS16 instructions."

test_file=./encodings.txt
if ! ${LLVM_BIN_DIR}llvm-mc --disassemble ${MIPS16_OPTS} ${test_file} > ${temp_file} ; then
    echo "llvm_mc FAILED"
    exit 1
fi

if ! ${LLVM_BIN_DIR}FileCheck ${test_file} < ${temp_file} ; then
    echo "FileCheck FAILED"
    exit 2
fi

echo "SUCCESS! We can decode MIPS16 instructions!"


echo "----------"
echo "ALL MIPS16 TESTS PASS!"
echo ""
exit 0