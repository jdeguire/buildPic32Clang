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
# Technology's PIC32 and SAM series of microcontroller and (eventually) microprocessor devices. The
# intent of pic32Clang is to provide a modern toolchain that supports the latest C and C++ standards
# and tools (such as Clang Tidy). Use this if you want to be able to use the latest those standards
# have to offer on your device and are willing to take some risk doing so. Use XC32 if you're
# looking for a seemless out-of-the-box experience that will just work with all of Microchip's
# tools, such as Harmony, and that is fully supported by a team of people who know what they're
# doing as opposed to the random dude on the internet that wrote this.
#
# This toolchain works in tandem with the toolchainPic32Clang plugin for the MPLAB X IDE to provide
# users with a fully-integrated experience similar to what one would get with a native Microchip
# product. The plugin will ensure that the proper options get passed to Clang when building, so at
# least try it out to see what that looks like, even if you do not plan to use MPLAB X full-time.
#
# In addition to Clang itself, this will build libraries needed to support the devices, including
# Musl libC, CMSIS for Arm devices, and support libraries for device-specific needs (such as startup
# code).
#

import argparse
import os
from pathlib import Path
import pic32_target_variants
import shutil
import subprocess
import time
import tkinter

PIC32_CLANG_VERSION = '0.01'
# SINGLE_STAGE_LLVM = False
SINGLE_STAGE_LLVM = True

# '/' is an operator for stuff in pathlib that joins path segments.
ROOT_WORKING_DIR = Path('./pic32clang')
BUILD_PREFIX = ROOT_WORKING_DIR / 'build'
INSTALL_PREFIX = ROOT_WORKING_DIR / 'install'

LLVM_REPO_URL = 'https://github.com/llvm/llvm-project.git'
#LLVM_RELEASE_BRANCH = 'llvmorg-11.0.1'
LLVM_RELEASE_BRANCH = ''
LLVM_SRC_DIR = ROOT_WORKING_DIR / 'llvm'

# Use my clone of Musl for now because it will contain mods to get it to work
# on our PIC32 and SAM devices.
#MUSL_REPO_URL = 'https://git.musl-libc.org/cgit/musl.git'
#MUSL_RELEASE_BRANCH = ''
MUSL_REPO_URL = 'https://github.com/jdeguire/musl.git'
MUSL_RELEASE_BRANCH = 'arm_cortex_m'
MUSL_SRC_DIR = ROOT_WORKING_DIR / 'musl'

CMAKE_CACHE_DIR = Path(os.path.dirname(os.path.realpath(__file__)), 'cmake_caches')


def get_dir_from_dialog(title: str | None = None, mustexist: bool = True) -> str:
    '''Open a file dialog asking the user to open a directory, returning what the user selects or
    None if the dialog is cancelled.

    The arguments let the caller specify a title for the dialog box and whether or not the choosen
    directory must already exist. 
    '''
    tk_root = tkinter.Tk()
    tk_root.withdraw()

    return tkinter.filedialog.askdirectory(title=title, mustexist=mustexist)


def is_windows():
    '''Return True if this script is running in a Windows environment. This returns False when run
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
    the command or executable and every item after are arguments. Normally, arguments are separated
    at the spaces in the command line. See the subprocess module for more info.

    The second argument is a string that will be always shown at the end of the output and is used
    to give info to the user about what the command is doing. This can be empty to show nothing.

    The third argument is the working directory that should be set before running the command. This
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
            # We need a number here or else this will block. On Unix, we can use os.set_blocking()
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
    # raise CalledProcessError. This will include the last bit of output from the command as that
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
    optional branch and output info. If the branch is None or empty, this will get the head of the
    master branch. If the destination directory is None or empty, this will create a subdirectory
    in the current working directory named after the project being cloned. If skip_if_exists is
    True, then this will look for and inhibit errors given by Git if the destination already exists;
    otherwise, the underlying subprocess code will throw a subprocess.CalledProcessError.
    '''
    cmd = ['git', 'clone']
# TODO: Use '--depth=1' to get a shallow clone
# TODO: For Windows, need to add '--config core.autocrlf=false (at least for LLVM)
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




def remake_dirs(dir):
    '''Remove and make the given directory and its subdirectories.
    
    Use this to remove build directories so that a clean build is done.'''
    if os.path.exists(dir):
        shutil.rmtree(dir)

    os.makedirs(dir)


def build_single_stage_llvm():
    '''Build LLVM and its associated projects as a single-stage build.

    This will remove any previous build directory so that a clean build is always performed. To
    avoid this, enter the directory using a command line and manually start a build from there.
    '''
    build_dir = BUILD_PREFIX / 'llvm'
    install_dir = os.path.relpath(INSTALL_PREFIX, build_dir)
    src_dir = os.path.relpath(LLVM_SRC_DIR / 'llvm', build_dir)

    remake_dirs(build_dir)

    gen_build_cmd = ['cmake', '-G', 'Ninja',
                     '-DCMAKE_INSTALL_PREFIX=' + install_dir,
                    #  '-DCMAKE_BUILD_TYPE=Debug',
                    #  '-DCMAKE_C_FLAGS_DEBUG=-O1 -g',
                    #  '-DCMAKE_CXX_FLAGS_DEBUG=-O1 -g',
                     '-DCMAKE_BUILD_TYPE=RelWithDebInfo',
                     '-DLLVM_ENABLE_LTO=OFF',
                     '-DLLVM_OPTIMIZED_TABLEGEN=ON',
                     '-DLLVM_USE_SPLIT_DWARF=ON',
                     '-DLLVM_TARGETS_TO_BUILD=ARM;Mips',
                     '-DLLVM_ENABLE_PROJECTS=clang;clang-tools-extra;lld;lldb;polly',
                     src_dir]
    run_subprocess(gen_build_cmd, 'Generate LLVM build script', build_dir)

    build_cmd = ['cmake', '--build', '.']
    run_subprocess(build_cmd, 'Build LLVM', build_dir)

    install_cmd = ['cmake', '--build', '.', '--target', 'install']
    run_subprocess(install_cmd, 'Install LLVM', build_dir)


def build_two_stage_llvm():
    '''Build LLVM and its associated projects using a 2-stage build.

    This will remove any previous build directory so that a clean build is always performed. To
    avoid this, enter the directory using a command line and manually start a build from there.
    '''
    build_dir = BUILD_PREFIX / 'llvm'
    install_dir = os.path.relpath(INSTALL_PREFIX, build_dir)
    src_dir = os.path.relpath(LLVM_SRC_DIR / 'llvm', build_dir)
    cmake_config_path = os.path.relpath(CMAKE_CACHE_DIR / 'pic32clang-llvm-stage1.cmake',
                                             build_dir)

    remake_dirs(build_dir)

    ######
    # The CMake cache files used here are based on the example configs found in
    # llvm/clang/cmake/caches that build a 2-stage distribution of LLVM/Clang. The 'stage1' cache
    # file already references the 'stage2' file, so we don't need to do anything with 'stage2' here.
    #
    # NOTE: By default, the CMake cache files build the stage2 compiler with LTO. This takes forever
    # and is not important for testing, so the below command disables it for now.
    #
    # TODO: There's a CMake variable called PACKAGE_VENDOR that could hold pic32Clang version info.
    #       There's also PACKAGE_VERSION, but that appears to have LLVM's version in it.
    #       Do I need something like this for Musl?
    gen_build_cmd = ['cmake', '-G', 'Ninja',
                     '-DCMAKE_INSTALL_PREFIX=' + install_dir,
                     '-DBOOTSTRAP_LLVM_ENABLE_LTO=OFF',
                     '-DBOOTSTRAP_CMAKE_BUILD_TYPE=RelWithDebInfo',
                     '-C', cmake_config_path,
                     src_dir]
    run_subprocess(gen_build_cmd, 'Generate LLVM build script', build_dir)

    build_cmd = ['cmake', '--build', '.', '--target', 'stage2-distribution']
    run_subprocess(build_cmd, 'Build LLVM', build_dir)

    install_cmd = ['cmake', '--build', '.', '--target', 'stage2-install-distribution']
    run_subprocess(install_cmd, 'Install LLVM', build_dir)


def get_lib_build_dir(libname, variant):
    '''Get a path relative to this script at which a library build will be performed.

    The path created depends on the path value in the given variant so that each variant has its own
    build directory.
    '''
    return BUILD_PREFIX / libname / variant.arch / variant.path


def get_lib_install_prefix(variant):
    '''Get a path relative to this script that would be used as the "prefix" path for installing the
    libraries.
    '''
    return INSTALL_PREFIX / variant.arch

def get_lib_info_str(variant):
    '''Get a string that can be printed to the console to indicate what variant is being built.
    '''
    return str(variant.arch / variant.path)


def get_lib_build_tool_path():
    '''Get the path relative to this script at which a built LLVM/Clang toolchain suitable for
    building the libraries in this script is located.
    
    This returns the top-level directory for the toolchain--that is, the path at which the bin/,
    lib/, and so on directories are located. This will use the stage 2 build location if able because
    the LLVM libraries make use of CMake caches and other build items in that location rather than 
    the final install location.
    '''
    if SINGLE_STAGE_LLVM:
        return BUILD_PREFIX / 'llvm'
    else:
        return BUILD_PREFIX / 'llvm' / 'tools' / 'clang' / 'stage2-bins'


def build_musl(variant):
    '''Build the Musl C library for a single variant.

    Build the Musl library for the given target variant using its build options. The build and install
    paths are determined by the path provided by the variant. This needs to be called after LLVM 
    itself has been built because this needs LLVM to build Musl. Musl is just one library, but for 
    compatibility with other C libraries Musl will build empty versions of libm, libpthread, and a 
    few others. 
    '''
    build_dir = get_lib_build_dir('musl', variant)
    prefix = get_lib_install_prefix(variant)
    prefix_dir = os.path.relpath(prefix, build_dir)
    lib_dir = os.path.relpath(prefix / 'lib' / variant.path, build_dir)
    src_dir = os.path.relpath(MUSL_SRC_DIR, build_dir)

    remake_dirs(build_dir)

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

    build_env = os.environ.copy()
    build_env['AR'] = os.path.abspath(get_lib_build_tool_path() / 'bin' / 'llvm-ar')
    build_env['RANLIB'] = os.path.abspath(get_lib_build_tool_path() / 'bin' / 'llvm-ranlib')
    build_env['CC'] = os.path.abspath(get_lib_build_tool_path() / 'bin' / 'clang')
    build_env['CFLAGS'] = ' '.join(variant.options) + ' -gline-tables-only'

# TODO: Does this need to specify a custom version string since this is my branch of Musl?
    gen_build_cmd = [src_dir + '/configure', 
                    '--prefix=' + prefix_dir,
                    '--libdir=' + lib_dir,
                    '--disable-shared',
                    '--disable-wrapper',
                    '--disable-optimize',
                    '--disable-debug',
                    '--target=' + variant.triple]
    gen_build_info = 'Configure Musl (' + get_lib_info_str(variant) + ')'
    run_subprocess(gen_build_cmd, gen_build_info, build_dir, penv=build_env)

    clean_cmd = ['make', 'clean']
    clean_info = 'Clean Musl (' + get_lib_info_str(variant) + ')'
    run_subprocess(clean_cmd, clean_info, build_dir, penv=build_env)

    build_cmd = ['make', '-j' + str(num_cpus)]
    build_info = 'Build Musl (' + get_lib_info_str(variant) + ')'
    run_subprocess(build_cmd, build_info, build_dir, penv=build_env)

    install_cmd = ['make', '-j1', 'install']
    install_info = 'Install Musl (' + get_lib_info_str(variant) + ')'
    run_subprocess(install_cmd, install_info, build_dir, penv=build_env)


def build_llvm_runtimes(variant):
    '''Build LLVM runtime libraries for a single build variant.

    Build libc++, libc++abi, libunwind, and Compiler-RT for the given build variant using its build
    options. The build and install paths of the libraries are determined by the path provided by the
    variant. This needs to be called after LLVM and Musl have been built.
    '''
    build_dir = get_lib_build_dir('runtimes', variant)
    prefix = get_lib_install_prefix(variant)
    prefix_dir = os.path.relpath(prefix, build_dir)
    src_dir = os.path.relpath(LLVM_SRC_DIR / 'runtimes', build_dir)

    clang_sysroot = os.path.abspath(get_lib_build_tool_path())
    cmake_config_path = os.path.relpath(CMAKE_CACHE_DIR / 'pic32clang-target-runtimes.cmake',
                                             build_dir)

    remake_dirs(build_dir)

    # Testing suggests that the CMake scripts for the runtimes detect the Arm variant (ie. armv6m)
    # from the triple rather than from the separate '-march=' option.
    if variant.arch.startswith('mips'):
        triple_str = variant.triple
    else:
        triple_str = variant.subarch + '-none-eabi'

    # TODO: The CMake script for the runtimes excludes the built-in atomics support because it fails
    #       with Armv6-m. It does not support the Arm atomic access instructions. Could we enable
    #       the atomics support for all other archs and leave out v6m?
    # TODO: Enable LTO and figure out if LTO libraries can be used in non-LTO builds.
    # TODO: The \' escapes may not be necessary.
    gen_build_cmd = ['cmake', '-G', 'Ninja', 
                     '-DCMAKE_INSTALL_PREFIX=\'' + prefix_dir + '\'',
                     '-DPIC32CLANG_LIBDIR_SUFFIX=\'' + str(variant.path) + '\'',
                     '-DPIC32CLANG_TARGET_TRIPLE=' + triple_str,
                     '-DPIC32CLANG_RUNTIME_FLAGS=' + ';'.join(variant.options),
                     '-DPIC32CLANG_SYSROOT=\'' + clang_sysroot + '\'',
                     '-C', cmake_config_path,
                     src_dir]
    gen_build_info = 'Generate runtimes build script (' + get_lib_info_str(variant) + ')'
    run_subprocess(gen_build_cmd, gen_build_info, build_dir)

    build_cmd = ['cmake', '--build', '.']
    build_info = 'Build runtimes (' + get_lib_info_str(variant) + ')'
    run_subprocess(build_cmd, build_info, build_dir)

    install_cmd = ['cmake', '--build', '.', '--target', 'install']
    install_info = 'Install runtimes (' + get_lib_info_str(variant) + ')'
    run_subprocess(install_cmd, install_info, build_dir)





# TODO: list for being always ready to try out a full build.
#
# --Call that script from here and then copy results to install dir.
# --Download CMSIS and put that into the correct spot. I might just need the header files.
# --Add CLI arguments to this script to select steps instead of updating this script manually.
# --Try running this on Windows. This might require using a thread to read from the subprocess.
#

# This is true when this file is executed as a script rather than imported into another file. We
# probably don't need this, but there's no harm in checking.
if '__main__' == __name__:
    # Windows 10 has supported ANSI escape codes for a while, but it has to be enabled and Python on
    # Windows (checked with 3.8) does not do that. This odd workaround came from
    # https://bugs.python.org/issue30075.
    if is_windows():
        subprocess.call('', shell=True)

    # clone_from_git(LLVM_REPO_URL, LLVM_RELEASE_BRANCH, LLVM_SRC_DIR, skip_if_exists=True)
    # clone_from_git(MUSL_REPO_URL, MUSL_RELEASE_BRANCH, MUSL_SRC_DIR, skip_if_exists=True)

    # if SINGLE_STAGE_LLVM:
    #     build_single_stage_llvm()
    # else:
    #     build_two_stage_llvm()

    build_variants = pic32_target_variants.create_build_variants()
    if True:
       for variant in build_variants:
           build_musl(variant)
           build_llvm_runtimes(variant)
    else:
       build_musl(build_variants[0])
       build_llvm_runtimes(build_variants[0])

    # Do this extra print because otherwise the info string will be below where the command prompt
    # re-appears after this ends.
    print('\n')
