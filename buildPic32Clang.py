#! /usr/bin/env python3
#
# Copyright (c) 2020, Jesse DeGuire
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# #####
#
# buildPic32Clang.py
#
# This is a script used to download and build an entire Clang-based toolchain for Microchip
# Technology's PIC32 and SAM series of microcontroller and (eventually) microprocessor devices.  The
# intent of pic32Clang is to provide a modern toolchain that supports the latest C and C++ standards
# and tools (such as Clang Tidy).  Use this if you want to be able to use the latest those standards
# have to offer on your device and are willing to take some risk doing so.  Use XC32 if you're
# looking for a seemless out-of-the-box experience that will just work with all of Microchip's
# tools, such as Harmony, and that is fully supported by a team of people who know what they're
# doing as opposed to the random dude on the internet that wrote this.
#
# This toolchain works in tandem with the toolchainPic32Clang plugin for the MPLAB X IDE to provide
# users with a fully-integrated experience similar to what one would get with a native Microchip
# product.  The plugin will ensure that the proper options get passed to Clang when building, so at
# least try it out to see what that looks like, even if you do not plan to use MPLAB X full-time.
#
# In addition to Clang itself, this will build libraries needed to support the devices, including
# Musl libC, CMSIS for Arm devices, and support libraries for device-specific needs (such as startup
# code).
#

PIC32_CLANG_VERSION = '0.01'

LLVM_REPO_URL = 'https://github.com/llvm/llvm-project.git'
LLVM_RELEASE_TAG = 'llvmorg-10.0.0'


import subprocess
import os
import time


def is_windows():
    '''Return True if this script is running in a Windows environment.  This returns False when run
    in a shell for the Windows Subsystem for Linux (WSL).
    '''
    return 'nt' == os.name

def clear_info_str():
    '''Use ANSI control codes to clear a previously-written info string from the console.
    '''
    print('\n\x1b[K\x1b[A', end='')

def print_info_str(s):
    '''Use ANSI control codes to print an info string in inverted colors to the end of the console
    output.
    '''
    print('\n\x1b[7m' + s + '\x1b[27m\x1b[K\r\x1b[A', end='', flush=True)

def run_subprocess(cmd_args, info_str, working_dir=None):
    '''Run the given command while printing the given step string at the end of output.

    Run the command given by the list cmd_args in which the first item in the list is the name of
    the command or executable and every item after are arguments.  Normally, arguments are separated
    at the spaces in the command line. See the subprocess module for more info.

    The second argument is a string that will be always shown at the end of the output and is used
    to give info to the user about what the command is doing.  This can be empty to show nothing.

    The third argument is the working directory that should be set before running the command.  This
    can be None to have the command use the current working directory (the directory from which this
    script was run).
    '''
    # Use ANSI control codes to put the info string on its own line and with reverse video (inverted
    # colors).
    if info_str:
        print_info_str(info_str)

    remaining_output = ''
    proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, 
                            cwd=working_dir, bufsize=0)

    while None == proc.poll():
        while True:
            # We need a number here or else this will block.  On Unix, we can use os.set_blocking()
            # to disable this, but not on Windows.
            output = proc.stdout.read(1024)
            if not output:
                break;

            out_lines = output.decode('utf-8').rsplit('\n', 1)
            if len(out_lines) > 1:
                # Found newline, so print what we found (rsplit removes the delimiter).
                # This first bit clears the info_string we wrote earlier.
                clear_info_str()
                print(remaining_output + out_lines[0] + '\n', end='')
                print_info_str(info_str)
                remaining_output = out_lines[1]
            else:
                print(remaining_output + out_lines[0], end='', flush=True)
                remaining_output = ''

        time.sleep(0.001)

    # Get any straggling lines after the process has ended
    remaining_output += proc.stdout.read().decode('utf-8')

    if remaining_output:
        clear_info_str()
        print(remaining_output, end='')
        print_info_str(info_str)

    # For now, emulate what subprocess.run() would have done, which is raise CalledProcessError.  Do
    # this to present a consistent error mechanism.  Things like invalid arguments or a missing
    # command will raise an exception, so we'll follow suit.  We won't include stdout or stderr
    # because it was already printed above and because there could be A LOT of it.
    if proc.returncode != 0:
        # This print makes sure that the info string is still visible when the Python exception info
        # is printed to the console.
        print('\n')
        raise subprocess.CalledProcessError(proc.returncode, cmd_args)


# This is true when this file is executed as a script rather than imported into another file.  We
# probably don't need this, but there's no harm in checking.
if '__main__' == __name__:
    # Windows 10 has supported ANSI escape codes for a while, but it has to be enabled and Python on
    # Windows (checked with 3.8) does not do that.  This odd workaround came from
    # https://bugs.python.org/issue30075.
    if is_windows():
        subprocess.call('', shell=True)

    #run_subprocess(['git', 'clone', '-b', LLVM_RELEASE_TAG, LLVM_REPO_URL],
    #               'Getting LLVM from Git!')
    run_subprocess(['python3', './test.py'],
                   'A rather long info string, wouldn\'t you say?  I mean, just look at it!')
    run_subprocess(['python3', './test.py'],
                   'This info string is also pretty long.  What are the odds of that?')

    # Do this extra print because otherwise the info string will be below where the command prompt
    # re-appears after this ends.
    print('\n')
