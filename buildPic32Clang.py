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

ROOT_WORKING_DIR = './pic32clang/'

LLVM_REPO_URL = 'https://github.com/llvm/llvm-project.git'
LLVM_RELEASE_BRANCH = 'llvmorg-10.0.0'
LLVM_WORKING_DIR = ROOT_WORKING_DIR + 'llvm/'

# Use a GitHub mirror for now since it can probably handle repeated clones I'll do while testing
# this better than a personal site.
#MUSL_REPO_URL = 'https://git.musl-libc.org/cgit/musl.git'
MUSL_REPO_URL = 'https://github.com/bminor/musl.git'
MUSL_RELEASE_BRANCH = 'v1.2.0'
MUSL_WORKING_DIR = ROOT_WORKING_DIR + 'musl/'

import subprocess
import os
import time
import shutil

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

    prev_output = ''
    remaining_output = ''
    proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, 
                            cwd=working_dir, bufsize=0)

    while None == proc.poll():
        while True:
            # We need a number here or else this will block.  On Unix, we can use os.set_blocking()
            # to disable this, but not on Windows.
            output = proc.stdout.read(256).decode('utf-8', 'backslashreplace')
            if not output:
                break;

            out_lines = output.rsplit('\n', 1)
            if len(out_lines) > 1:
                # Found newline, so print what we found (rsplit removes the delimiter).
                clear_info_str()
                print(remaining_output + out_lines[0] + '\n', end='')
                print_info_str(info_str)
                remaining_output = out_lines[1]
            else:
                print(remaining_output + out_lines[0], end='', flush=True)
                remaining_output = ''

            prev_output = output

        time.sleep(0.001)

    # Get any straggling lines after the process has ended
    remaining_output += proc.stdout.read().decode('utf-8', 'backslashreplace')

    if remaining_output:
        clear_info_str()
        print(remaining_output, end='')
        print_info_str(info_str)

    # For now, emulate what subprocess.run() would have done on a non-zero return code, which is
    # raise CalledProcessError.  This will include the last bit of output from the command as that
    # may have some useful error info worth checking or showing.
    if proc.returncode != 0:
        # This print makes sure that the info string is still visible when the Python exception info
        # is printed to the console.
        print('\n')
        except_output = prev_output + output + remaining_output
        raise subprocess.CalledProcessError(proc.returncode, cmd_args, except_output)


def clone_from_git(url, branch=None, dest_directory=None, skip_if_exists=False):
    '''Clone a git repo from the given url.

    Clone a git repo by calling out to the locally-installed git executable with the given URL and
    optional branch and output info.  If the branch is None or empty, this will get the head of the
    master branch.  If the destination directory is None or empty, this will create a subdirectory
    in the current working directory named after the project being cloned.  If skip_if_exists is
    True, then this will look for and inhibit errors given by Git if the destination already exists;
    otherwise, the underlying subprocess code will throw a subprocess.CalledProcessError.
    '''
    cmd = ['git', 'clone']

    if branch:
        cmd.append('-b')
        cmd.append(branch)

    cmd.append(url)

    if dest_directory:
        cmd.append(dest_directory)

    try:
        run_subprocess(cmd, 'Cloning ' + url)
    except subprocess.CalledProcessError as ex:
        if skip_if_exists  and  'already exists' in ex.output:
            pass
        else:
            raise

# Notes:
# -- Devices for which the datasheet claims as MIPS32r5 also have an FPU and vice versa. These are 
#    the PIC32MZ EF and PIC32MK devices. All other devices with no FPU are assumed to be MIPS32r2.
# -- Devices with an FPU also have the DSPr2 extension, but not vice versa. The PIC32MZ DA and
#    PIC32MZ EC have DSPr2, but not an FPU.
# -- The previous note implies that all MIPS32r5 devices have the DSPr2 extension.
# -- Only the PIC32MX series uses the older MIPS16 extension; none of them have an FPU or DSP ASE.
MIPS32_MULTILIB_PREFIX = 'target/mips32/lib/'
MIPS32_MULTILIBS = ['r2',
                    'r2/mips16',
                    'r2/micromips',
                    'r2/micromips/dspr2', 
                    'r2/dspr2',
                    'r5/dspr2',
                    'r5/dspr2/fpu64',
                    'r5/micromips/dspr2',
                    'r5/micromips/dspr2/fpu64']

def get_mips_multilib_opts(multilib_path):
    '''Return a string containing compiler options for a MIPS device based on the given multilib path.
    '''
    split_path = multilib_path.split('/')
    opts = '-target mipsel-unknown-elf'

    # MIPS32 architecture revision
    if 'r5' in split_path:
        opts += ' -march=mips32r5'
    else:
        opts += ' -march=mips32r2'

    # Compressed instruction set support
    if 'mips16' in split_path:
        opts += ' -mips16'
    if 'micromips' in split_path:
        opts += ' -mmicromips'

    # Application-specific Extensions (ASEs); only DSPr2 at this time.
    if 'dspr2' in split_path:
        opts += ' -mdspr2'

    # FPU
    if 'fpu64' in split_path:
        opts += ' -mhard-float -mfloat-abi=hard -mfp64'
    else:
        opts += ' -msoft-float -mfloat-abi=soft'

    # This option prevents libraries from putting small globals into the small data sections. This
    # is the safest option since an application can control the size threshold with '-G<size>'.
    opts += ' -G0'

    return opts

# Notes:
# -- The M0, M0+, M23, and M3 do not have an FPU.
# -- The M4 has a 32-bit FPU.
# -- The M7 has a 64-bit FPU.
# -- The A5 can have either a normal 64-bit FPU or one with NEON.
# -- The M series is always Thumb, so we do not have to differentiate.
CORTEX_M_MULTLIB_PREFIX = 'target/cortex-m/lib/'
CORTEX_M_MULTILIBS = ['m0plus',
                      'm23',
                      'm3',
                      'm4',
                      'm4/vfp4-sp-d16',
                      'm7',
                      'm7/vfp5-dp-d16']

CORTEX_A_MULTILIB_PREIX = 'target/cortex-a/lib/'
CORTEX_A_MULTILIBS = ['a5',
                      'a5/vfp4-dp-d16',
                      'a5/neon-vfpv4',
                      'a5/thumb',
                      'a5/thumb/vfp4-dp-d16',
                      'a5/thumb/neon-vfpv4']

def get_arm_multilib_opts(multilib_path):
    '''Return a string containing compiler options for an Arm device based on the given multilib path.
    '''
    split_path = multilib_path.split('/')
    opts = '-target arm-none-eabi'

    # CPU name
    if 'm0plus' in split_path:
        opts += ' -march=armv6m -mtune=cortex-m0plus'
    elif 'm23' in split_path:
        opts += ' -march=armv8m.base -mtune=cortex-m23'
    elif 'm3' in split_path:
        opts += ' -march=armv7m -mtune=cortex-m3'
    elif 'm4' in split_path:
        opts += ' -march=armv7em -mtune=cortex-m4'
    elif 'm7' in split_path:
        opts += ' -march=armv7em -mtune=cortex-m7'
    elif 'a5' in split_path:
        opts += ' -march=armv7a -mtune=cortex-a5'

    # Compressed instruction set
    if 'thumb' in split_path:
        opts += ' -mthumb'

    # FPU name
    if 'vfp4-sp-d16' in split_path:
        opts += ' -mfpu=vfp4-sp-d16 -mfloat-abi=hard'
    elif 'vfp4-dp-d16' in split_path:
        opts += ' -mfpu=vfp4-dp-d16 -mfloat-abi=hard'
    elif 'vfp5-dp-d16' in split_path:
        opts += ' -mfpu=vfp5-dp-d16 -mfloat-abi=hard'
    elif 'fp-armv8' in split_path:
        opts += ' -mfpu=fp-armv8 -mfloat-abi=hard'
    elif 'neon-vfpv4' in split_path:
        opts += ' -mfpu=neon-vfpv4 -mfloat-abi=hard'
    else:
        opts += ' -msoft-float -mfloat-abi=soft'

    return opts

OPTIMIZATION_MULTILIBS = ['',
                          'o1',
                          'o2',
                          'o3',
                          'os',
                          'ofast',
                          'oz',
                          'fast-math',
                          'fast-math/o1',
                          'fast-math/o2',
                          'fast-math/o3',
                          'fast-math/os',
                          'fast-math/ofast',
                          'fast-math/oz']

def get_optimization_multilib_opts(multilib_path):
    '''Return a string containing optimization options based on the given multilib path.
    '''
    split_path = multilib_path.split('/')
    opts = ''

    # Specific flags (just fast math for now)
    if 'fast-math' in split_path:
        opts += ' -ffast-math'

    # Optimization level
    if 'o1' in split_path:
        opts += ' -O1'
    elif 'o2' in split_path:
        opts += ' -O2'
    elif 'o3' in split_path:
        opts += ' -O3'
    elif 'os' in split_path:
        opts += ' -Os'
    elif 'ofast' in split_path:
        opts += ' -Ofast'
    elif 'oz' in split_path:
        opts += ' -Oz'
    else:
        opts += ' -O0'


def build_llvm():
    '''Build LLVM and its associated projects.

    This will remove any previous build directory so that a clean build is always performed. To
    avoid this, enter the directory using a command line and manually start a build from there.
    '''
    llvm_build_dir = LLVM_WORKING_DIR + 'build/'

    if os.path.exists(llvm_build_dir):
        shutil.rmtree(llvm_build_dir)

    os.mkdir(llvm_build_dir)

    llvm_targets = ['ARM', 'Mips']
    llvm_projects = ['clang', 'clang-tools-extra', 'compiler-rt', 'debuginfo-tests', 'libc',
                     'libclc', 'libcxx', 'libcxxabi', 'libunwind', 'lld', 'lldb', 'mlir', 'openmp',
                     'parallel-libs', 'polly', 'pstl']

    gen_build_cmd = ['cmake', '-G', 'Ninja', 
                     '-DCMAKE_BUILD_TYPE=Release',
                     '-DCMAKE_INSTALL_PREFIX=../../install',
                     '-DLLVM_TARGETS_TO_BUILD=' + ';'.join(llvm_targets),
                     '-DLLVM_ENABLE_PROJECTS=' + ';'.join(llvm_projects),
                     '../llvm']
    run_subprocess(gen_build_cmd, 'Generate LLVM build scripts', llvm_build_dir)

    build_llvm_cmd = ['cmake', '--build', '.']
    run_subprocess(build_llvm_cmd, 'Build LLVM', llvm_build_dir)


# This is true when this file is executed as a script rather than imported into another file.  We
# probably don't need this, but there's no harm in checking.
if '__main__' == __name__:
    # Windows 10 has supported ANSI escape codes for a while, but it has to be enabled and Python on
    # Windows (checked with 3.8) does not do that.  This odd workaround came from
    # https://bugs.python.org/issue30075.
    if is_windows():
        subprocess.call('', shell=True)

    #run_subprocess(['git', 'clone', '-b', LLVM_RELEASE_BRANCH, LLVM_REPO_URL],
    #               'Getting LLVM from Git!')
    #run_subprocess(['python3', './test.py'],
    #               'A rather long info string, wouldn\'t you say?  I mean, just look at it!')
    #run_subprocess(['python3', './test.py'],
    #               'This info string is also pretty long.  What are the odds of that?')
    clone_from_git(LLVM_REPO_URL, LLVM_RELEASE_BRANCH, LLVM_WORKING_DIR, skip_if_exists=True)
    clone_from_git(MUSL_REPO_URL, MUSL_RELEASE_BRANCH, MUSL_WORKING_DIR, skip_if_exists=True)

    build_llvm()

    # Do this extra print because otherwise the info string will be below where the command prompt
    # re-appears after this ends.
    print('\n')
