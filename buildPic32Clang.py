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

import subprocess
import os
import time
import shutil
from pathlib import PurePosixPath, Path


PIC32_CLANG_VERSION = '0.01'

# Note that '/' is an operator for stuff in pathlib that joins path segments.
ROOT_WORKING_DIR = PurePosixPath('.', 'pic32clang')
BUILD_PREFIX = ROOT_WORKING_DIR / 'build'
INSTALL_PREFIX = ROOT_WORKING_DIR / 'install'

LLVM_REPO_URL = 'https://github.com/llvm/llvm-project.git'
LLVM_RELEASE_BRANCH = 'llvmorg-11.0.1'
LLVM_WORKING_DIR = ROOT_WORKING_DIR / 'llvm'

# Use my clone of Musl for now because it will contain mods to get it to work
# on our PIC32 and SAM devices.
#MUSL_REPO_URL = 'https://git.musl-libc.org/cgit/musl.git'
#MUSL_RELEASE_BRANCH = ''
MUSL_REPO_URL = 'https://github.com/jdeguire/musl.git'
MUSL_RELEASE_BRANCH = 'v1.2.2_baremetal'
MUSL_WORKING_DIR = ROOT_WORKING_DIR / 'musl'

CMAKE_CACHE_DIR = PurePosixPath(os.path.dirname(os.path.realpath(__file__)), 'cmake_caches')


def is_windows():
    '''Return True if this script is running in a Windows environment.  This returns False when run
    in a shell for the Windows Subsystem for Linux (WSL).
    '''
    return 'nt' == os.name


def print_line_with_info_str(line, info_str):
    '''Print the given line while also using ANSI control codes to print the given info string in 
    inverted colors below it. The cursor will be on a new line when this is done.
    '''
    # Finish the current line before moving to the next by printing everything before the first newline.
    split_line = line.split('\n', 1)
    print(split_line[0], end='')

    # Control codes start with \x1b (ESC) and [
    #   '7m' enables inverted colors (reverse video)
    #   '27m' disabled inverted colors
    #   'K' clears the rest of the line starting at the cursor
    #   'A' moves up one line
    print('\n\x1b[K\x1b[A', end='')
    if len(split_line) > 1:
        print('\n' + split_line[1], end='')
    print('\n\n\x1b[7m' + info_str + '\x1b[27m\x1b[K\r\x1b[A', end='', flush=True)


def run_subprocess(cmd_args, info_str, working_dir=None, penv=None, use_shell=False):
    '''Run the given command while printing the given step string at the end of output.

    Run the command given by the list cmd_args in which the first item in the list is the name of
    the command or executable and every item after are arguments.  Normally, arguments are separated
    at the spaces in the command line. See the subprocess module for more info.

    The second argument is a string that will be always shown at the end of the output and is used
    to give info to the user about what the command is doing.  This can be empty to show nothing.

    The third argument is the working directory that should be set before running the command.  This
    can be None to have the command use the current working directory (the directory from which this
    script was run). This can be a string or a path-like object, such as something from pathlib.

    The fourth argument is a map of environment variables to use. If this is None, then the
    environment is inherited from this process. Otherwise, it must be a map in which the keys are
    the variables names and the values are the variable values.

    The fifth argument indicates if the process needs to be run in a terminal shell. This generally
    would be needed only if the command were a shell command, such as 'ls' on a Bash shell or 'dir'
    on the Windows command prompt, or shell scripts like the 'configure' that many projects use. If
    this is True, then 'cmd_args' should be a single string formatted just like it would be if the
    command were typed into the terminal. See the Python documentation for subprocess.Popen() for
    more info.
    '''
    if info_str:
        print_line_with_info_str('', info_str)

    output = ''
    prev_output = ''
    remaining_output = ''
    proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, 
                            cwd=working_dir, bufsize=0, env=penv, shell=use_shell)

    while None == proc.poll():
        while True:
            # We need a number here or else this will block.  On Unix, we can use os.set_blocking()
            # to disable this, but not on Windows.
            output = proc.stdout.read(2048).decode('utf-8', 'backslashreplace')
            if not output:
                break

            out_lines = output.rsplit('\n', 1)
            if len(out_lines) > 1:
                # Found newline, so print what we found (rsplit removes the delimiter).
                print_line_with_info_str(remaining_output + out_lines[0], info_str)
                remaining_output = out_lines[1]
            else:
                print(remaining_output + out_lines[0], end='', flush=True)
                remaining_output = ''

            prev_output = output

        time.sleep(0.001)

    # Get any straggling lines after the process has ended
    remaining_output += proc.communicate()[0].decode('utf-8', 'backslashreplace')

    if remaining_output:
        print_line_with_info_str(remaining_output, info_str)

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
# -- It's not clear if Clang/LLVM cares about r2 vs r5 (it might only care about r6 vs rest).
# -- MIPS16 is commented out for now because Clang/LLVM can crash when trying to use it.
# -- microMIPS + FPU is commented out for now because Clang/LLVM can crash when trying to use it.
MIPS32_MULTILIB_PREFIX = PurePosixPath('target', 'mips32', 'lib')
MIPS32_MULTILIBS = [PurePosixPath('r2'),
#                    PurePosixPath('r2', 'mips16'),
                    PurePosixPath('r2', 'micromips'),
                    PurePosixPath('r2', 'micromips', 'dspr2'), 
                    PurePosixPath('r2', 'dspr2'),
                    PurePosixPath('r5', 'dspr2'),
                    PurePosixPath('r5', 'dspr2', 'fpu64'),
#                    PurePosixPath('r5', 'micromips', 'dspr2'),
#                    PurePosixPath('r5', 'micromips', 'dspr2', 'fpu64')
                    ]

def get_mips_multilib_opts(multilib_path):
    '''Return a string array containing compiler options for a MIPS device based on the given
    pathlib.Path object representing a multilib path.
    '''
    opts = ['-target', 'mipsel-linux-gnu-musl']

    # MIPS32 architecture revision
    if 'r5' in multilib_path.parts:
        opts.append('-march=mips32r5')
    else:
        opts.append('-march=mips32r2')

    # Compressed instruction set support
    if 'mips16' in multilib_path.parts:
        opts.append('-mips16')
    if 'micromips' in multilib_path.parts:
        opts.append('-mmicromips')

    # Application-specific Extensions (ASEs); only DSPr2 at this time.
    if 'dspr2' in multilib_path.parts:
        opts.append('-mdspr2')

    # FPU
    if 'fpu64' in multilib_path.parts:
        opts.append('-mhard-float')
        opts.append('-mfp64')
    else:
        opts.append('-msoft-float')

    # This option prevents libraries from putting small globals into the small data sections. This
    # is the safest option since an application can control the size threshold with '-G<size>'.
    opts.append('-G0')
    opts.append('-fomit-frame-pointer')

    return opts


# Notes:
# -- The M0, M0+, M23, and M3 do not have an FPU.
# -- The M4 has a 32-bit FPU; the M7 has a 64-bit FPU. These are Armv7em.
# -- The A5 can have either a normal 64-bit FPU or one with NEON. This is Armv7a.
# -- The M series is always Thumb, so we do not have to differentiate.
ARM_MULTLIB_PREFIX = PurePosixPath('target', 'arm', 'lib')
ARM_MULTILIBS = [PurePosixPath('v6m'),
                 PurePosixPath('v7m'),
                 PurePosixPath('v7em'),
                 PurePosixPath('v7em', 'fpv4-sp-d16'),
                 PurePosixPath('v7em', 'fpv5-d16'),
                 PurePosixPath('v8m.base'),
#                 PurePosixPath('v8m.main'),
#                 PurePosixPath('v8m.main', 'fpv5-sp-d16'),
#                 PurePosixPath('v8.1m.main'),
#                 PurePosixPath('v8.1m.main', 'fp-armv8-fullfp16-d16')
                 PurePosixPath('v7a'),
                 PurePosixPath('v7a', 'vfpv4-d16'),
                 PurePosixPath('v7a', 'neon-vfpv4'),
                 PurePosixPath('v7a', 'thumb'),
                 PurePosixPath('v7a', 'thumb', 'vfpv4-d16'),
                 PurePosixPath('v7a', 'thumb', 'neon-vfpv4')]

def get_arm_multilib_opts(multilib_path):
    '''Return a string array containing compiler options for an Arm device based on the given
    pathlib.Path object representing a multilib path.
    '''
    opts = ['-target', 'arm-none-eabi-musl']

    # Architecture name
    if 'v6m' in multilib_path.parts:
        opts.append('-march=armv6m')
    elif 'v7m' in multilib_path.parts:
        opts.append('-march=armv7m')
    elif 'v7em' in multilib_path.parts:
        opts.append('-march=armv7em')
    elif 'v7a' in multilib_path.parts:
        opts.append('-march=armv7a')
    elif 'v8m.base' in multilib_path.parts:
        opts.append('-march=armv8m.base')
    elif 'v8m.main' in multilib_path.parts:
        opts.append('-march=armv8m.main')
    elif 'v8.1m.main' in multilib_path.parts:
        if 'fp-armv8-fullfp16-d16' in multilib_path.parts:
            opts.append('-march=armv8.1m.main+mve.fp+fp.dp')
        else:
            opts.append('-march=armv8.1m.main')

    # Compressed instruction set
    if 'thumb' in multilib_path.parts:
        opts.append('-mthumb')

    # FPU name
    if 'fpv4-sp-d16' in multilib_path.parts:
        opts.append('-mfpu=fpv4-sp-d16')
        opts.append('-mfloat-abi=hard')
    elif 'vfpv4-d16' in multilib_path.parts:
        opts.append('-mfpu=vfpv4-d16')
        opts.append('-mfloat-abi=hard')
    elif 'fpv5-sp-d16' in multilib_path.parts:
        opts.append('-mfpu=fpv5-sp-d16')
        opts.append('-mfloat-abi=hard')
    elif 'fpv5-d16' in multilib_path.parts:
        opts.append('-mfpu=fpv5-d16')
        opts.append('-mfloat-abi=hard')
    elif 'fp-armv8' in multilib_path.parts:
        opts.append('-mfpu=fp-armv8')
        opts.append('-mfloat-abi=hard')
    elif 'fp-armv8-fullfp16-d16' in multilib_path.parts:
        opts.append('-mfpu=fp-armv8-fullfp16-d16')
        opts.append('-mfloat-abi=hard')
    elif 'neon-vfpv4' in multilib_path.parts:
        opts.append('-mfpu=neon-vfpv4')
        opts.append('-mfloat-abi=hard')
    else:
        opts.append('-msoft-float')
        opts.append('-mfloat-abi=soft')

    opts.append('-fomit-frame-pointer')
    opts.append('-mimplicit-it=always')

    return opts


OPTIMIZATION_MULTILIBS = [PurePosixPath('.'),
                          PurePosixPath('o1'),
                          PurePosixPath('o2'),
                          PurePosixPath('o3'),
                          PurePosixPath('os'),
                          PurePosixPath('oz')]

def get_optimization_multilib_opts(multilib_path):
    '''Return a string array containing optimization options based on the given pathlib.Path object
    representing a multilib path.
    '''
    opts = []

    if 'o1' in multilib_path.parts:
        opts.append('-O1')
    elif 'o2' in multilib_path.parts:
        opts.append('-O2')
    elif 'o3' in multilib_path.parts:
        opts.append('-O3')
    elif 'os' in multilib_path.parts:
        opts.append('-Os')
    elif 'oz' in multilib_path.parts:
        opts.append('-Oz')
    else:
        opts.append('-O0')

    return opts


def build_llvm():
    '''Build LLVM and its associated projects.

    This will remove any previous build directory so that a clean build is always performed. To
    avoid this, enter the directory using a command line and manually start a build from there.
    '''
    llvm_build_dir = BUILD_PREFIX / 'llvm'
    llvm_install_dir = os.path.relpath(INSTALL_PREFIX, llvm_build_dir)
    llvm_src_dir = os.path.relpath(LLVM_WORKING_DIR / 'llvm', llvm_build_dir)
    llvm_cmake_config_path = os.path.relpath(CMAKE_CACHE_DIR / 'pic32clang-llvm-stage1.cmake',
                                             llvm_build_dir)

    if os.path.exists(llvm_build_dir):
        shutil.rmtree(llvm_build_dir)

    os.makedirs(llvm_build_dir)

    ######
    # The CMake cache files used here are based on the example configs found in
    # llvm/clang/cmake/caches that build a 2-stage distribution of LLVM/Clang. The 'stage1' cache
    # file already references the 'stage2' file, so we don't need to do anything with 'stage2' here.
    # The commented-out lines here contain all of the projects, but we'll start with what the
    # examples had.
    #
    # NOTE: By default, the CMake cache files build the stage2 compiler with LTO. This takes forever
    # and is not important for testing, so the below command disables it for now.
    #
    # TODO: Can the DEFAULT_SYSROOT option be set such that it is always relative to the executables?
    #       It looks like setting it to ".." might make it relative to where the "bin/" directory is.
    gen_build_cmd = ['cmake', '-G', 'Ninja',
                     '-DCMAKE_INSTALL_PREFIX=' + llvm_install_dir,
                     '-DBOOTSTRAP_LLVM_ENABLE_LTO=OFF',
                     '-C', llvm_cmake_config_path,
                     llvm_src_dir]
    run_subprocess(gen_build_cmd, 'Generate LLVM build script', llvm_build_dir)

    build_llvm_cmd = ['cmake', '--build', '.', '--target', 'stage2-distribution']
    run_subprocess(build_llvm_cmd, 'Build LLVM', llvm_build_dir)

    install_llvm_cmd = ['cmake', '--build', '.', '--target', 'stage2-install-distribution']
    run_subprocess(install_llvm_cmd, 'Install LLVM', llvm_build_dir)


def build_musl():
    '''Build the Musl C library for the targets.

    This needs to be called after LLVM itself has been built because this needs LLVM to build Musl.
    Musl is just one library, but for compatibility with other C libraries Musl will build empty
    versions of libm, libpthread, and a few others. 
    '''
    musl_build_dir = BUILD_PREFIX / 'musl'
    musl_install_dir = os.path.relpath(INSTALL_PREFIX / 'musl', musl_build_dir)
    musl_src_dir = os.path.relpath(MUSL_WORKING_DIR, musl_build_dir)

    clang_c_path = os.path.abspath(INSTALL_PREFIX / 'bin' / 'clang')
    llvm_ar_path = os.path.abspath(INSTALL_PREFIX / 'bin' / 'llvm-ar')
    llvm_ranlib_path = os.path.abspath(INSTALL_PREFIX / 'bin' / 'llvm-ranlib')

    if os.path.exists(musl_build_dir):
        shutil.rmtree(musl_build_dir)

    os.makedirs(musl_build_dir)

    num_cpus = os.cpu_count()
    if None == num_cpus or num_cpus < 1:
        num_cpus = 1
#    num_cpus = 1

    #####
    # Notes:
    # --We need -mimplicit-it=always when building this for Thumb2 (and probably Thumb). This is
    #   probably because I'm giving Musl a target of arm-none-eabi rather than armv7m-none-eabi.
    # --We need -fomit-frame-pointer on at least Armv6-m or else Clang will complain that a syscall 
    #   routine uses up too many registers.
    # --The configure script just generates a config.mak file in the build directory. It might be easier
    #   to either just generate that here or add all of those value to the environment. This would mean
    #   not having to run the script on Windows, but it does mean we may fall behind script updates.
    # --For Armv7(E)-M and Armv8M/8.1M Mainline, Clang defines both __thumb__ and __thumb2__.
    # --For Armv6-M and Armv8-M.base, only __thumb__ is defined.

    musl_env = os.environ.copy()
    musl_env['AR'] = llvm_ar_path
    musl_env['RANLIB'] = llvm_ranlib_path
    musl_env['CC'] = clang_c_path

    for mips_ml in MIPS32_MULTILIBS:
        multilib_opts = ' '.join(get_mips_multilib_opts(mips_ml))

        for opt_ml in OPTIMIZATION_MULTILIBS:
            multilib_str = str('mips32' / mips_ml / opt_ml)
            prefix_str = str(PurePosixPath(musl_install_dir, multilib_str))
            optimization_opts = ' '.join(get_optimization_multilib_opts(opt_ml))

            musl_env['CFLAGS'] = multilib_opts + ' ' + optimization_opts

# TODO: This needs to specify the '--includedir' and '--libdir' options (and maybe others, check Configure)
#       to put files where we really want them.
            gen_build_cmd = [musl_src_dir + '/configure', 
                            '--prefix=' + prefix_str,
                            '--disable-shared',
                            '--disable-wrapper',
                            '--disable-optimize',
                            '--enable-debug',
                            '--target=mipsel-linux-gnu-musl']
            gen_build_info = 'Configure Musl (' + multilib_str + ')'
            run_subprocess(gen_build_cmd, gen_build_info, musl_build_dir, penv=musl_env)

            clean_musl_cmd = ['make', 'clean']
            clean_musl_info = 'Clean Musl (' + multilib_str + ')'
            run_subprocess(clean_musl_cmd, clean_musl_info, musl_build_dir, penv=musl_env)

            build_musl_cmd = ['make', '-j' + str(num_cpus)]
            build_musl_info = 'Build Musl (' + multilib_str + ')'
            run_subprocess(build_musl_cmd, build_musl_info, musl_build_dir, penv=musl_env)

            install_musl_cmd = ['make', '-j1', 'install']
            install_musl_info = 'Install Musl (' + multilib_str + ')'
            run_subprocess(install_musl_cmd, install_musl_info, musl_build_dir, penv=musl_env)
        
    for arm_ml in ARM_MULTILIBS:
        multilib_opts = ' '.join(get_arm_multilib_opts(arm_ml))

        for opt_ml in OPTIMIZATION_MULTILIBS:
            multilib_str = str('arm' / arm_ml / opt_ml)
            prefix_str = str(PurePosixPath(musl_install_dir, multilib_str))
            optimization_opts = ' '.join(get_optimization_multilib_opts(opt_ml))

            musl_env['CFLAGS'] = multilib_opts + ' ' + optimization_opts

            gen_build_cmd = [musl_src_dir + '/configure', 
                            '--prefix=' + prefix_str,
                            '--disable-shared',
                            '--disable-wrapper',
                            '--disable-optimize',
                            '--enable-debug',
                            '--target=arm-none-eabi-musl']
            gen_build_info = 'Configure Musl (' + multilib_str + ')'
            run_subprocess(gen_build_cmd, gen_build_info, musl_build_dir, penv=musl_env)

            clean_musl_cmd = ['make', 'clean']
            clean_musl_info = 'Clean Musl (' + multilib_str + ')'
            run_subprocess(clean_musl_cmd, clean_musl_info, musl_build_dir, penv=musl_env)

            build_musl_cmd = ['make', '-j' + str(num_cpus)]
            build_musl_info = 'Build Musl (' + multilib_str + ')'
            run_subprocess(build_musl_cmd, build_musl_info, musl_build_dir, penv=musl_env)

            install_musl_cmd = ['make', '-j1', 'install']
            install_musl_info = 'Install Musl (' + multilib_str + ')'
            run_subprocess(install_musl_cmd, install_musl_info, musl_build_dir, penv=musl_env)


def build_llvm_runtimes():
    '''Build LLVM runtime libraries for the targets.

    This needs to be called after LLVM itself has been built because this needs LLVM to build the
    target libraries.
    '''
    musl_include_path = os.path.abspath(INSTALL_PREFIX / 'musl' / 'mips32' / 'r2' / 'include')
    cxx_include_path = os.path.abspath(INSTALL_PREFIX / 'runtimes' / 'include' / 'c++' / 'v1')

    # Use the stage2 compiler location instead of the final install location because this has
    # llvm-config and all the CMake cache files it looks for to determine how to build libraries.
    compiler_prefix = BUILD_PREFIX / 'llvm' / 'tools' / 'clang' / 'stage2-bins'

    clang_sysroot = os.path.abspath(compiler_prefix)
    clang_c_path = os.path.abspath(compiler_prefix / 'bin' / 'clang')
    clang_cxx_path = os.path.abspath(compiler_prefix / 'bin' / 'clang++')
    llvm_ar_path = os.path.abspath(compiler_prefix / 'bin' / 'llvm-ar')
    llvm_nm_path = os.path.abspath(compiler_prefix / 'bin' / 'llvm-nm')
    llvm_ranlib_path = os.path.abspath(compiler_prefix / 'bin' / 'llvm-ranlib')

    rt_os_dir_name = 'baremetal'

    rt_flags = [
    ### This is arch-specific stuff.
                '-target', 'mipsel-linux-gnu-musl',
                '-march=mips32r2',
                '-msoft-float',
                '-G0',
                '-static',
                '-fomit-frame-pointer',

    ### This is stuff that will apply to every build.
    #            '-v',
                '-isystem\'' + musl_include_path + '\'',
    # Undefine these so that the output is the same regardless of build platform.
    # Otherwise, libc++ will use platform-specific code based on which is defined.
                '-U__linux__',
                '-U__APPLE__',
                '-U_WIN32',
    # These are defined if libc++ is configured to use Musl and __linux__ is defined.
    # Define them manually so that they work the same regardless of build platform.
                '-D_LIBCPP_HAS_ALIGNED_ALLOC',
                '-D_LIBCPP_HAS_QUICK_EXIT',
                '-D_LIBCPP_HAS_TIMESPEC_GET',
                '-D_LIBCPP_HAS_C11_FEATURES'
               ]

    rt_build_dir = BUILD_PREFIX / 'runtimes'
    rt_src_dir = os.path.relpath(LLVM_WORKING_DIR / 'llvm' / 'runtimes', rt_build_dir)
    rt_install_prefix = os.path.relpath(INSTALL_PREFIX / 'runtimes', rt_build_dir)
    multilib_str = 'mips32/r2'

    if os.path.exists(rt_build_dir):
        shutil.rmtree(rt_build_dir)

    os.makedirs(rt_build_dir)

    # TODO: Break this up and use individual CMake caches.
    # TODO: Enable LTO and figure out if LTO libraries can be used in non-LTO builds.
    gen_build_cmd = ['cmake', '-G', 'Ninja', 
                     '-DCMAKE_CROSSCOMPILING=ON',
                     '-DCMAKE_SYSROOT=\'' + clang_sysroot + '\'',
                     '-DCMAKE_C_COMPILER=\'' + clang_c_path + '\'',
                     '-DCMAKE_CXX_COMPILER=\'' + clang_cxx_path + '\'',
                     '-DCMAKE_C_COMPILER_TARGET=mipsel-linux-gnu-musl',
                     '-DCMAKE_CXX_COMPILER_TARGET=mipsel-linux-gnu-musl',
                     '-DCMAKE_ASM_COMPILER_TARGET=mipsel-linux-gnu-musl',
                     '-DCMAKE_AR=\'' + llvm_ar_path + '\'',
                     '-DCMAKE_NM=\'' + llvm_nm_path + '\'',
                     '-DCMAKE_RANLIB=\'' + llvm_ranlib_path + '\'',
                     '-DCMAKE_BUILD_TYPE=Release',
                     '-DCMAKE_INSTALL_PREFIX=\'' + rt_install_prefix + '\'',
                     '-DCMAKE_C_FLAGS=\'' + ' '.join(rt_flags) + '\'',
                     '-DCMAKE_CXX_FLAGS=\'' + ' '.join(rt_flags) + '\'',
    # TODO: CMAKE_SYSTEM_NAME will probably need to be "Linux" to get anything other than
    #       the basic builtins.
    #                 '-DCMAKE_SYSTEM_NAME=Generic',
                     '-DCMAKE_SYSTEM_NAME=Linux',
    # TODO: Remove this linker flag when LLVM is rebuilt to use LLD by default.
    #                 '-DCMAKE_EXE_LINKER_FLAGS=-fuse-ld=lld',
                     '-DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY',

                     '-DLLVM_INCLUDE_DOCS=ON',
                     '-DLLVM_ENABLE_SPHINX=ON',
    # TODO: Maybe figure out if this flag can be removed, but the checks fail because they need
    #       libraries I haven't yet built.
                     '-DLLVM_COMPILER_CHECKED=ON',
                     '-DLLVM_ENABLE_RUNTIMES=all',

    # TODO: Fool CMake into thinking we're targeting Linux for the runtimes because otherwise
    #       the CMake checks will fail with being unable to determine the target platform.
    #       That's probably because I set CMAKE_SYSTEM_NAME to "Generic" above, but I don't know
    #       if removing that will affect things on Windows vs Linux builds.
    # These should not be needed if I set the system name to Linux.
    #                 '-DUNIX=ON',
    #                 '-DWIN32=OFF',
    #                 '-DAPPLE=OFF',
    #                 '-DFUSCHIA=OFF',

                     '-DCOMPILER_RT_OS_DIR=' + rt_os_dir_name,
                     '-DCOMPILER_RT_BAREMETAL_BUILD=ON',
                     '-DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON',
                     '-DCOMPILER_RT_STANDALONE_BUILD=ON',
    # We can build only the builtins now.
                     '-DCOMPILER_RT_BUILD_BUILTINS=ON',
                     '-DCOMPILER_RT_BUILD_CRT=OFF',
                     '-DCOMPILER_RT_BUILD_SANITIZERS=OFF',
                     '-DCOMPILER_RT_BUILD_XRAY=OFF',
                     '-DCOMPILER_RT_BUILD_LIBFUZZER=OFF',
                     '-DCOMPILER_RT_BUILD_PROFILE=OFF',
                     '-DCOMPILER_RT_USE_BUILTINS_LIBRARY=ON',
                     '-DCOMPILER_RT_EXCLUDE_ATOMIC_BUILTIN=OFF',

                     '-DLIBUNWIND_ENABLE_STATIC=ON',
                     '-DLIBUNWIND_ENABLE_SHARED=OFF',
                     '-DLIBUNWIND_USE_COMPILER_RT=ON',
                     '-DLIBUNWIND_ENABLE_CROSS_UNWINDING=OFF',

                     '-DLIBCXX_HAS_MUSL_LIBC=ON',
                     '-DLIBCXX_STANDALONE_BUILD=ON',
                     '-DLIBCXX_ENABLE_STATIC=ON',
                     '-DLIBCXX_ENABLE_SHARED=OFF',
                     '-DLIBCXX_ENABLE_FILESYSTEM=ON',
                     '-DLIBCXX_ENABLE_EXPERIMENTAL_LIBRARY=ON',
                     '-DLIBCXX_CXX_ABI=libcxxabi',
                     '-DLIBCXX_USE_COMPILER_RT=ON',
                     '-DLIBCXX_USE_LLVM_UNWINDER=ON',
                     '-DLIBCXX_HAS_PTHREAD_API=ON',

                     '-DLIBCXXABI_BAREMETAL=ON',
                     '-DLIBCXXABI_STANDALONE_BUILD=ON',
                     '-DLIBCXXABI_ENABLE_STATIC=ON',
                     '-DLIBCXXABI_ENABLE_SHARED=OFF',
                     '-DLIBCXXABI_USE_LLVM_UNWINDER=ON',
                     '-DLIBCXXABI_USE_COMPILER_RT=ON',
                     '-DLIBCXXABI_HAS_PTHREAD_API=ON',
                     '-DLIBCXXABI_LIBCXX_INCLUDES=\'' + cxx_include_path + '\'',

                     rt_src_dir]
    run_subprocess(gen_build_cmd, 'Generate runtimes build script (' + multilib_str + ')', rt_build_dir)

    # Generate and install the C++ headers first because libcxxabi will need them.
    install_cxx_headers_cmd = ['cmake', '--build', '.', '--target', 'install-cxx-headers']
    run_subprocess(install_cxx_headers_cmd, 'Generate C++ Headers (' + multilib_str + ')', rt_build_dir)

    build_rt_cmd = ['cmake', '--build', '.']
    run_subprocess(build_rt_cmd, 'Build runtimes (' + multilib_str + ')', rt_build_dir)

    install_rt_cmd = ['cmake', '--build', '.', '--target', 'install']
    run_subprocess(install_rt_cmd, 'Install runtimes (' + multilib_str + ')', rt_build_dir)



# This is true when this file is executed as a script rather than imported into another file.  We
# probably don't need this, but there's no harm in checking.
if '__main__' == __name__:
    # Windows 10 has supported ANSI escape codes for a while, but it has to be enabled and Python on
    # Windows (checked with 3.8) does not do that.  This odd workaround came from
    # https://bugs.python.org/issue30075.
    if is_windows():
        subprocess.call('', shell=True)

    clone_from_git(LLVM_REPO_URL, LLVM_RELEASE_BRANCH, LLVM_WORKING_DIR, skip_if_exists=True)
    clone_from_git(MUSL_REPO_URL, MUSL_RELEASE_BRANCH, MUSL_WORKING_DIR, skip_if_exists=True)

    #print("\n*****\nBUILD LLVM COMMENTED OUT\n*****\n")
    #build_llvm()

    #print("\n*****\nBUILD MUSL COMMENTED OUT\n*****\n")
    #build_musl()

    #print("\n*****\nBUILD RUNTIMES COMMENTED OUT\n*****\n")
    build_llvm_runtimes()

    # Do this extra print because otherwise the info string will be below where the command prompt
    # re-appears after this ends.
    print('\n')
