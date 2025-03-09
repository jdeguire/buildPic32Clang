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
# the LLVM runtimes, CMSIS for Arm devices, and support libraries for device-specific needs (such
# as startup code).
#

import argparse
import os
from pathlib import Path
import pic32_target_variants
from pic32_target_variants import TargetVariant
import shutil
import subprocess
import time
import tkinter
import tkinter.filedialog

# These are the build steps this script can do. The steps to be done can be given on the 
# command line or 'all' can be used to do all of these.
ALL_BUILD_STEPS = ['clone', 'llvm', 'runtimes', 'devfiles', 'cmsis', 'startup']

PIC32_CLANG_VERSION = '0.01'
PIC32_CLANG_PROJECT_URL = 'https://github.com/jdeguire/buildPic32Clang'

# '/' is an operator for stuff in pathlib that joins path segments.
ROOT_WORKING_DIR = Path('./pic32clang')
BUILD_PREFIX = ROOT_WORKING_DIR / 'build'
INSTALL_PREFIX = ROOT_WORKING_DIR / 'install'

THIS_FILE_DIR = Path(os.path.dirname(os.path.realpath(__file__)))
CMAKE_CACHE_DIR = THIS_FILE_DIR / 'cmake_caches'
LIBC_CONFIG_DIR = THIS_FILE_DIR / 'llvm_libc_config'

LLVM_REPO_URL = 'https://github.com/llvm/llvm-project.git'
LLVM_REPO_BRANCH = 'llvmorg-20.1.0'
LLVM_SRC_DIR = ROOT_WORKING_DIR / 'llvm'

PIC32_FILE_MAKER_REPO_URL = 'https://github.com/jdeguire/pic32-device-file-maker.git'
PIC32_FILE_MAKER_SRC_DIR = ROOT_WORKING_DIR / 'pic32-device-file-maker'

CMSIS_REPO_URL = 'https://github.com/ARM-software/CMSIS_6.git'
CMSIS_REPO_BRANCH = 'v6.1.0'
CMSIS_SRC_DIR = ROOT_WORKING_DIR / 'cmsis'



def get_dir_from_dialog(title: str | None = None, mustexist: bool = True) -> str | None:
    '''Open a file dialog asking the user to open a directory, returning what the user selects or
    None if the dialog is cancelled.

    The arguments let the caller specify a title for the dialog box and whether or not the choosen
    directory must already exist. 
    '''
    tk_root = tkinter.Tk()
    tk_root.withdraw()
    return tkinter.filedialog.askdirectory(title=title, mustexist=mustexist)


def is_windows() -> bool:
    '''Return True if this script is running in a Windows environment.
    
    This returns False when run in a shell for the Windows Subsystem for Linux (WSL).
    '''
    return 'nt' == os.name


def get_cmake_bool(sel: bool) -> str:
    '''Return ON or OFF based on the given boolean for use with CMake commands.
    '''
    return 'ON' if sel else 'OFF'


def get_lib_build_dir(libname: str, variant: TargetVariant) -> Path:
    '''Get a path relative to the working directory from which this script was run at which a
    library build will be performed.

    The path created depends on the path value in the given variant so that each variant has its own
    build directory.
    '''
    return BUILD_PREFIX / libname / variant.series / variant.path


def get_lib_install_prefix(variant: TargetVariant) -> Path:
    '''Get a path relative to the working directory from which this script was run that would be
    used as the "prefix" path for installing the libraries.
    '''
    return INSTALL_PREFIX / variant.series

def get_lib_info_str(variant: TargetVariant) -> str:
    '''Get a string that can be printed to the console to indicate what variant is being built.
    '''
    return str(variant.series / variant.path)


def get_lib_build_tool_abspath(args: argparse.Namespace) -> Path:
    '''Get the absolute path to the just-built LLVM/Clang toolchain so it can be used to build
    the libraries.

    This returns the top-level directory for the toolchain--that is, the path at which the bin/,
    lib/, and so on directories are located. This will use the stage 2 build location if able because
    the LLVM libraries make use of CMake caches and other build items in that location rather than 
    the final install location.
    '''
    if args.single_stage:
        libpath = BUILD_PREFIX / 'llvm'
    else:
        libpath = BUILD_PREFIX / 'llvm' / 'tools' / 'clang' / 'stage2-bins'

    return libpath.absolute()


def remake_dirs(dir: Path) -> None:
    '''Remove and make the given directory and its subdirectories.
    
    Use this to remove build directories so that a clean build is done.
    '''
    if dir.exists():
        shutil.rmtree(dir)

    os.makedirs(dir)


def print_line_with_info_str(line: str, info_str: str) -> None:
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


def run_subprocess(cmd_args: list[str], info_str: str, working_dir: Path | None = None, 
                   penv: dict[str, str] | None = None, use_shell: bool = False,
                   echo_cmd: bool = False) -> None:
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

    The final argument indicates if the command should be printed into the output. If True, each
    element in the command list will be separated by a single space.
    '''
    if info_str:
        if echo_cmd:
            print_line_with_info_str(' '.join(cmd_args), info_str)
        else:
            print_line_with_info_str('', info_str)
    elif echo_cmd:
        print(' '.join(cmd_args))

    output = ''
    prev_output = ''
    remaining_output = ''
    proc = subprocess.Popen(cmd_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=False, 
                            cwd=working_dir, bufsize=0, env=penv, shell=use_shell)

    while None == proc.poll()  and  proc.stdout:
        while True:
            # We need a number here or else this will block. On Unix, we can use os.set_blocking()
            # to disable this, but not on Windows.
            output = proc.stdout.read(4096).decode('utf-8', 'backslashreplace')
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


def clone_from_git(url: str, branch: str = '', dest_directory: Path | None = None,
                   skip_if_exists: bool = False, full_clone: bool = False) -> None:
    '''Clone a git repo from the given url.

    Clone a git repo by calling out to the locally-installed git executable with the given URL and
    optional branch and output info. If the branch is None or empty, this will get the head of the
    master branch. If the destination directory is None or empty, this will create a subdirectory
    in the current working directory named after the project being cloned. If skip_if_exists is
    True, then this will look for and inhibit errors given by git if the destination already exists;
    otherwise, the underlying subprocess code will throw a subprocess.CalledProcessError. If 
    full_clone is True, then this will clone the full repo history; otherwise, only a shallow clone
    is made by using the "--depth=1" option.

    To clone a branch and then switch to a particular commit, append a colon and the hash for the
    desired commit to the branch name. For example, 'foo:123adcdef' will clone branch 'foo' and then
    switch to commit '123abcdef'.
    '''
    cmd = ['git', 'clone']
    commit = ''

    if not full_clone:
        cmd.append('--depth=1')

    if branch:
        parts = branch.split(':', 1)
        cmd.append('-b')
        cmd.append(parts[0])

        if len(parts) > 1:
            commit = parts[1]

    if is_windows():
        cmd.append('--config')
        cmd.append('core.autocrlf=false')

    cmd.append(url)

    if dest_directory:
        cmd.append(dest_directory.as_posix())

    if not full_clone  and  commit:
        raise ValueError('You must perform a full clone to checkout a particular commit')

    try:
        run_subprocess(cmd, 'Cloning ' + url)

        if commit:
            run_subprocess(['git', 'checkout', commit], 'Checking out commit ' + commit)
    except subprocess.CalledProcessError as ex:
        if skip_if_exists  and  'already exists' in ex.output:
            pass
        else:
            raise

def clone_selected_repos_from_git(args: argparse.Namespace) -> None:
    '''Clone repos from git based on the build steps and command line arguments to this script.
    '''
    if args.clone_all  or  'llvm' in args.steps  or  'runtimes' in args.steps:
        clone_from_git(LLVM_REPO_URL, args.llvm_branch, LLVM_SRC_DIR, 
                    skip_if_exists=args.skip_existing, full_clone=args.full_clone)

    if args.clone_all or 'devfiles' in args.steps:
        clone_from_git(PIC32_FILE_MAKER_REPO_URL, '', PIC32_FILE_MAKER_SRC_DIR, 
                    skip_if_exists=args.skip_existing, full_clone=args.full_clone)

    if args.clone_all or 'cmsis' in args.steps:
        clone_from_git(CMSIS_REPO_URL, args.cmsis_branch, CMSIS_SRC_DIR, 
                    skip_if_exists=args.skip_existing, full_clone=args.full_clone)


def build_single_stage_llvm(args: argparse.Namespace) -> None:
    '''Build LLVM and its associated projects as a single-stage build.

    This will remove any previous build directory so that a clean build is always performed. To
    avoid this, enter the directory using a command line and manually start a build from there.
    '''
    build_dir = BUILD_PREFIX / 'llvm'
    install_dir = Path(os.path.relpath(INSTALL_PREFIX, build_dir))
    src_dir = Path(os.path.relpath(LLVM_SRC_DIR / 'llvm', build_dir))

    remake_dirs(build_dir)

    # TODO: Can I use the stage2 cmake cache for this?
    gen_cmd = [
        'cmake', '-G', 'Ninja',
        f'-DCMAKE_INSTALL_PREFIX={install_dir.as_posix()}',
        f'-DCMAKE_BUILD_TYPE={args.llvm_build_type}',
        f'-DLLVM_ENABLE_LTO={get_cmake_bool(args.enable_lto)}',
        f'-DLLVM_PARALLEL_COMPILE_JOBS={args.compile_jobs}',
        f'-DLLVM_PARALLEL_LINK_JOBS={args.link_jobs}',
        '-DCLANG_CONFIG_FILE_SYSTEM_DIR=../config',
        '-DLLVM_OPTIMIZED_TABLEGEN=ON',
        '-DLLVM_USE_SPLIT_DWARF=ON',
        '-DLLVM_TARGETS_TO_BUILD=host;ARM;Mips',
        '-DLLVM_ENABLE_PROJECTS=clang;clang-tools-extra;lld;lldb;polly',
        src_dir.as_posix()
    ]
    run_subprocess(gen_cmd, 'Generate LLVM build script', build_dir)

    build_cmd = ['cmake', '--build', '.']
    run_subprocess(build_cmd, 'Build LLVM', build_dir)

    install_cmd = ['cmake', '--build', '.', '--target', 'install']
    run_subprocess(install_cmd, 'Install LLVM', build_dir)


def build_two_stage_llvm(args: argparse.Namespace) -> None:
    '''Build LLVM and its associated projects using a 2-stage build.

    This will remove any previous build directory so that a clean build is always performed. To
    avoid this, enter the directory using a command line and manually start a build from there.
    '''
    build_dir = BUILD_PREFIX / 'llvm'
    install_dir = Path(os.path.relpath(INSTALL_PREFIX, build_dir))
    src_dir = Path(os.path.relpath(LLVM_SRC_DIR / 'llvm', build_dir))
    cmake_config_path = Path(os.path.relpath(CMAKE_CACHE_DIR / 'pic32clang-llvm-stage1.cmake',
                                             build_dir))

    remake_dirs(build_dir)

    ######
    # The CMake cache files used here are based on the example configs found in
    # llvm/clang/cmake/caches that build a 2-stage distribution of LLVM/Clang. The 'stage1' cache
    # file already references the 'stage2' file, so we don't need to do anything with 'stage2' here.
    #
    # TODO: There's a CMake variable called PACKAGE_VENDOR that could hold pic32Clang version info.
    #       There's also PACKAGE_VERSION, but that appears to have LLVM's version in it.
    #       Do I put that in the stage1 or stage2 file? Do I add BOOTSTRAP_ to the start? I think so
    #       since anything starting with BOOTSTRAP_ is passed to the stage2 build automatically.
    gen_cmd = [
        'cmake', '-G', 'Ninja',
        f'-DCMAKE_INSTALL_PREFIX={install_dir.as_posix()}',
        f'-DBOOTSTRAP_LLVM_ENABLE_LTO={get_cmake_bool(args.enable_lto)}',
        f'-DBOOTSTRAP_CMAKE_BUILD_TYPE={args.llvm_build_type}',
        f'-DLLVM_PARALLEL_COMPILE_JOBS={args.compile_jobs}',
        f'-DLLVM_PARALLEL_LINK_JOBS={args.link_jobs}',
        f'-DBOOTSTRAP_LLVM_PARALLEL_COMPILE_JOBS={args.compile_jobs}',
        f'-DBOOTSTRAP_LLVM_PARALLEL_LINK_JOBS={args.link_jobs}',
        '-C', cmake_config_path.as_posix(),
        src_dir.as_posix()
    ]
    run_subprocess(gen_cmd, 'Generate LLVM build script', build_dir)

    build_cmd = ['cmake', '--build', '.', '--target', 'stage2-distribution']
    run_subprocess(build_cmd, 'Build LLVM', build_dir)

    install_cmd = ['cmake', '--build', '.', '--target', 'stage2-install-distribution']
    run_subprocess(install_cmd, 'Install LLVM', build_dir)


def add_stdio_file_decls() -> None:
    '''Add a minimal set of file I/O function declarations to LLVM-libc stdio.h to get libc++ to
    build, such as vfprintf(), feof(), ferror(), and so on.
    '''
    stdio_h_path: Path = INSTALL_PREFIX / 'cortex-m' / 'include' / 'stdio.h'
    stdio_list: list[str] = []
    update_index: int = -1

    # First, read the current file into a list. Each line is an element of the list.
    with open(stdio_h_path, 'r', encoding='utf-8') as stdio_in:
        stdio_list = list(stdio_in)

    # Now, check if the file has already been updated. For now, we'll just look for one file IO
    # function declaration and assume we already updated the file if we see it.
    for line_no, line_str in enumerate(stdio_list):
        if 'vfprintf' in line_str:
            # Found this, so assume file was already updated.
            break

        if '__END_C_DECLS' in line_str:
            # Found end of declarations, so remember where we are so we can add our declarations.
            update_index = line_no
            break

    if update_index < 0:
        return
    
    # We need to update the file, so overwrite it while adding our new declarations.
    with open(stdio_h_path, 'w', encoding='utf-8') as stdio_out:
        for line_no, line_str in enumerate(stdio_list):
            if line_no == update_index:
                stdio_out.write('/* Manually added minimal stdio file functions needed for libc++.\n')
                stdio_out.write('   Users will need to implement these own their own. */\n')
                stdio_out.write('int fprintf(FILE *__restrict, const char *__restrict, ... ) __NOEXCEPT;\n')
                stdio_out.write('int vfprintf(FILE *__restrict, const char *__restrict, va_list) __NOEXCEPT;\n')
                stdio_out.write('size_t fwrite(const void *__restrict, size_t, size_t, FILE *__restrict) __NOEXCEPT;\n')
                stdio_out.write('int ferror(FILE *) __NOEXCEPT;\n')
                stdio_out.write('int feof(FILE *) __NOEXCEPT;\n')
                stdio_out.write('int fflush(FILE *) __NOEXCEPT;\n')
                stdio_out.write('\n')

            stdio_out.write(line_str)


def build_llvm_runtimes(args: argparse.Namespace, variant: TargetVariant):
    '''Build LLVM runtime libraries for a single build variant.

    Build libc, libc++, libc++abi, libunwind, and Compiler-RT for the given build variant using its
    build options. The build and install paths of the libraries are determined by the path provided
    by the variant. This needs to be called after LLVM has been built.
    '''
    build_dir = get_lib_build_dir('runtimes', variant)
    prefix = get_lib_install_prefix(variant)
    prefix_dir = Path(os.path.relpath(prefix, build_dir))
    src_dir = Path(os.path.relpath(LLVM_SRC_DIR / 'runtimes', build_dir))

    clang_sysroot = get_lib_build_tool_abspath(args)
    cmake_config_path = Path(os.path.relpath(CMAKE_CACHE_DIR / 'pic32clang-target-runtimes.cmake',
                                             build_dir))
    libc_config_path = LIBC_CONFIG_DIR / 'arm'

    # This suffix goes up a level because the LLVM CMake scripts add an extra '/lib/' we don't want.
    # These paths match the ones in our multilib.yaml file. That is generated as part of the 'devfiles'
    # step. We add '/lib' to the end because LLVM does after parsing multilib.yaml.
    libdir_suffix = Path(f'../{variant.path.as_posix()}/lib')

    remake_dirs(build_dir)

    # Testing suggests that the CMake scripts for the runtimes detect the Arm variant (ie. armv6m)
    # from the triple rather than from the separate '-march=' option.
    if variant.series.startswith('mips'):
        triple_str = variant.triple
    else:
        triple_str = variant.arch + '-none-eabi'

    # TODO: The CMake script for the runtimes excludes the built-in atomics support because it fails
    #       with Armv6-m. It does not support the Arm atomic access instructions. Could we enable
    #       the atomics support for all other archs and leave out v6m?
    options_str = ';'.join(variant.options)
    gen_cmd = [
        'cmake', '-G', 'Ninja', 
        f'-DCMAKE_INSTALL_PREFIX={prefix_dir.as_posix()}',
        f'-DCMAKE_BUILD_TYPE={args.llvm_build_type}',
        f'-DLIBC_CONFIG_PATH={libc_config_path.as_posix()}',
        f'-DPIC32CLANG_LIBDIR_SUFFIX={libdir_suffix.as_posix()}',
        f'-DPIC32CLANG_TARGET_TRIPLE={triple_str}',
        f'-DPIC32CLANG_RUNTIME_FLAGS={options_str}',
        f'-DPIC32CLANG_SYSROOT={clang_sysroot.as_posix()}',
        f'-DLLVM_PARALLEL_COMPILE_JOBS={args.compile_jobs}',
        f'-DLLVM_PARALLEL_LINK_JOBS={args.link_jobs}',
        '-C', cmake_config_path.as_posix(),
        src_dir.as_posix()
    ]
    gen_build_info = f'Generate runtimes build script ({get_lib_info_str(variant)})'
    run_subprocess(gen_cmd, gen_build_info, build_dir)

    run_subprocess(['cmake', '--build', '.', '--target', 'install-compiler-rt'],
                   f'Build/Install Compiler-RT ({get_lib_info_str(variant)})',
                   build_dir)

    run_subprocess(['cmake', '--build', '.', '--target', 'install-libc'],
                   f'Build/Install LLVM-libc ({get_lib_info_str(variant)})',
                   build_dir)

    add_stdio_file_decls()

    run_subprocess(['cmake', '--build', '.', '--target', 'install-unwind'],
                   f'Build/Install libcxxabi ({get_lib_info_str(variant)})',
                   build_dir)

    run_subprocess(['cmake', '--build', '.', '--target', 'install-cxxabi'],
                   f'Build/Install libcxxabi ({get_lib_info_str(variant)})',
                   build_dir)

    run_subprocess(['cmake', '--build', '.', '--target', 'install-cxx'],
                   f'Build/Install libcxx ({get_lib_info_str(variant)})',
                   build_dir)

    # Compiler-RT is built to include the arch name in the library name unless we let CMake decide
    # the directories to install them (option LLVM_ENABLE_PER_TARGET_RUNTIME_DIR). That ends up
    # being a pain for other reasons, but we need to remove the arch from the library name to help
    # Clang find Compiler-RT in our arch-specific directory structure.
    # TODO: Armv8.1m.main targets with MVE are missing these files. Did we mess up or did the build?
    compiler_rt_path = prefix / variant.path / 'lib'
    for crt in compiler_rt_path.iterdir():
        if '-' in crt.name:
            if crt.name.startswith('libclang_rt.'):
                subname = crt.stem[12:].split('-', 1)
                new_path = crt.parent / f'libclang_rt.{subname[0]}{crt.suffix}'
                
                new_path.unlink(missing_ok=True)    
                crt.rename(new_path)
            elif crt.name.startswith('clang_rt.'):
                subname = crt.stem[9:].split('-', 1)
                new_path = crt.parent / f'clang_rt.{subname[0]}{crt.suffix}'

                new_path.unlink(missing_ok=True)    
                crt.rename(new_path)

    # LLVM-libc puts the outputs into a per-target directory. We already handle this, so move the
    # libc files up a level to be with the rest of the libraries.
    libc_path = prefix / variant.path / 'lib' / triple_str
    for libc in libc_path.iterdir():
        new_path = libc.parent.parent / libc.name
        new_path.unlink(missing_ok=True)
        libc.rename(libc.parent.parent / libc.name)
    libc_path.rmdir()

def build_device_files(args: argparse.Namespace) -> None:
    '''Build the device-specific files like headers file and linker scripts.
    '''
    build_dir = BUILD_PREFIX / 'pic32-device-file-maker'
    output_dir = Path(os.path.relpath(build_dir, PIC32_FILE_MAKER_SRC_DIR))

    # Run the maker app.
    #
    build_cmd = [
        'python3', './pic32-device-file-maker.py',
        '--parse-jobs', str(args.compile_jobs),
        '--output-dir', output_dir.as_posix(),
        args.packs_dir.resolve().as_posix()
    ]
    run_subprocess(build_cmd, 'Make device-specifc files', PIC32_FILE_MAKER_SRC_DIR)

    # Now copy the created files into the install location.
    #
    print('Copying device files to their proper location...', end='')
    shutil.copytree(build_dir / 'pic32-device-files',
                    INSTALL_PREFIX,
                    dirs_exist_ok=True)
    print('Done!')


def build_device_startup_files() -> None:
    '''Build the startup files for each device into crt0.o object files.

    The device config files are set up such that the toolchain will look for crt0.o in the
    device-specific directories, so this will put the object files there. This step requires that
    all of the other steps have been completed (except for maybe the library and runtime builds).
    This does not stop if a device build fails. A summary of failed devices is printed at the end
    if there were any failed builds.
    '''
    crt0_dir: Path = INSTALL_PREFIX / 'cortex-m' / 'proc'
    failed_devices: list[str] = []

    if is_windows():
        compiler_path = Path(os.path.abspath(INSTALL_PREFIX / 'bin' / 'clang.exe'))
    else:
        compiler_path = Path('../../../bin/clang')

    for proc_dir in crt0_dir.iterdir():
        if not proc_dir.is_dir():
            continue

        try:
            build_cmd = [
                compiler_path.as_posix(),
                '--config', f'{proc_dir.name}.cfg',
                '-Os',
                '-ffunction-sections',
                '-c',
                '-o', 'crt0.o',
                'startup.c'
            ]
            run_subprocess(build_cmd, 
                        f'Build startup (crt0.o) for {proc_dir.name.upper()}',
                        proc_dir,
                        echo_cmd = True)
        except subprocess.CalledProcessError as err:
            devname = proc_dir.name.upper()
            failed_devices.append(devname)
            print(f'Building startup code for {devname} failed with:')
            print('    ' + str(err))

    if failed_devices:
        print(f'----------\nStartup code for {len(failed_devices)} devices failed to build:')
        print('\n'.join(failed_devices))


def copy_cmsis_files() -> None:
    '''Copy the CMSIS header files to their proper spot in the source tree.

    For CMSIS, there is nothing to build and so this just needs to copy files.
    '''
    print('Copying CMSIS files to their proper location...', end='')
    shutil.copytree(CMSIS_SRC_DIR / 'CMSIS',
                    INSTALL_PREFIX / 'CMSIS',
                    dirs_exist_ok = True)
    print('Done!')


def get_command_line_arguments() -> argparse.Namespace:
    '''Return a object containing command line arugments for this script.

    If an error occurs or a command line arugment requests help text or version info, then this will
    exit the program after printing the appropriate info instead of returning.
    '''
    desc_str = \
        'Build a complete Clang toolchain for your PIC32 and SAM devices (Cortex-M only for now).' 

    epilog_str = \
        'See the README file for more information about the arguments and running this script.'        

    version_str = \
        f'buildPic32Clang {PIC32_CLANG_VERSION} ({PIC32_CLANG_PROJECT_URL})'

    # Create a help formatter that gives a bit more space between the option and help text.
    # The default seems to be 24 characters. This solution was found on:
    # https://stackoverflow.com/questions/52605094/python-argparse-increase-space-between-parameter-and-description
    wider_formatter = lambda prog: argparse.ArgumentDefaultsHelpFormatter(prog, max_help_position=28)

    parser = argparse.ArgumentParser(description=desc_str, 
                                     epilog=epilog_str,
                                     formatter_class=wider_formatter)

    # The '-h, --help' options are automatically added. The 'version' action on the '--version'
    # option is special and will exit after printing the version string.
    parser.add_argument('--steps',
                        nargs='+',
                        default=['all'],
                        type=str.lower,
                        choices=ALL_BUILD_STEPS + ['all'],
                        metavar=('STEP', 'STEPS'),
                        help='select the build steps this script should perform')
    parser.add_argument('--packs-dir',
                        default='show dialog',
                        metavar='DIR',
                        help='set location of packs directory to be read')
    parser.add_argument('--llvm-build-type',
                        default='Release',
                        choices=['Release', 'Debug', 'RelWithDebInfo', 'MinSizeRel'],
                        metavar='TYPE',
                        help='select CMake build type to use for LLVM (does not apply to libraries)')
    parser.add_argument('--llvm-branch',
                        default=LLVM_REPO_BRANCH,
                        metavar='REF',
                        help='select LLVM git branch to clone from (use "main" to get latest)')
    parser.add_argument('--cmsis-branch',
                        default=CMSIS_REPO_BRANCH,
                        metavar='REF',
                        help='select CMSIS git branch to clone from (use "main" to get latest)')
    parser.add_argument('--clone-all',
                        action='store_true',
                        help='clone every git repo even if not needed')
    parser.add_argument('--full-clone',
                        action='store_true',
                        help='clone the fully history of git repos')
    parser.add_argument('--skip-existing',
                        action='store_true',
                        help='skip cloning repos that already exist instead of raising an exception')
    parser.add_argument('--enable-lto',
                        action='store_true',
                        help='enable Link Time Optimization for LLVM')
    parser.add_argument('--single-stage',
                        action='store_true',
                        help='do a single-stage LLVM build instead of two-stage')
    parser.add_argument('--compile-jobs',
                        type=int,
                        default=0,
                        metavar='JOBS',
                        help='number of parallel compile jobs')
    parser.add_argument('--link-jobs',
                        type=int,
                        default=0,
                        metavar='JOBS',
                        help='number of parallel link jobs')
    parser.add_argument('--version', action='version',
                        version=version_str)

    # The command-line arguments added above will be a part of the returned object as member
    # variables. For example, 'args.output_dir' holds the argument for '--output_dir'.
    return parser.parse_args()


def process_command_line_arguments(args: argparse.Namespace) -> None:
    '''Look for sentinel values in the arguments and turn them into useful values.
    '''
    # Check the 'steps' argument to see if we should do everything.
    #
    if 'all' in args.steps:
        args.steps = ALL_BUILD_STEPS

    # Check the 'packs_dir' argument to see if we need to pop up a dialog box and then ensure the
    # directory exists. This is needed only if we want to create the device files.
    #
    if 'devfiles' in args.steps:
        if 'show dialog' == args.packs_dir:
            selected_dir = get_dir_from_dialog('Select packs directory', mustexist=True)

            if not selected_dir:
                print('Packs directory dialog was cancelled; exiting.')
                exit(0)
            else:
                args.packs_dir = Path(selected_dir)
        else:
            args.packs_dir = Path(args.packs_dir)

        if not args.packs_dir.exists():
            print('You need to specify an existing packs directory when the "devfiles" step is active')
            print(f'The directory specified was {args.packs_dir.as_posix()}')
            exit(0)

    # Check if we need to set a useful value for the number of compile and link jobs. Limit the max
    # jobs to the number of CPUs available. This will pick a reasonable default if the number of
    # CPUs could not be determined for some reason.
    #
    max_jobs: int | None = os.cpu_count()

    if max_jobs is None:
        max_jobs = 2

    if args.compile_jobs <= 0  or  args.compile_jobs > max_jobs:
        args.compile_jobs = max_jobs

    if args.link_jobs <= 0  or  args.link_jobs > max_jobs:
        args.link_jobs = max_jobs


def print_arg_info(args: argparse.Namespace) -> None:
    '''Print some info indicating what arguments were selected, which might be useful for logging.
    '''
    print('Here are the arguments this script is using (some may be set from defaults):')
    print('----------')
    print(f'Selected steps: {args.steps}')
    print(f'Build type: {args.llvm_build_type}')
    print(f'LLVM branch: {args.llvm_branch}')
    print(f'CMSIS branch: {args.cmsis_branch}')
    print(f'Packs directory: {args.packs_dir}')
    print(f'Compile jobs: {args.compile_jobs}')
    print(f'Link jobs: {args.link_jobs}')

    if os.path.exists(args.packs_dir):
        print('Packs dir found')
    else:
        print('Packs dir not found')

    if args.single_stage:
        print('Single stage build selected')
    else:
        print('Will do two-stage build')

    if args.enable_lto:
        print('LTO enabled')
    else:
        print('LTO disabled')

    if args.full_clone:
        print('Doing a full clone of the git repos')
    else:
        print('Doing a shallow clone of the git repos')
    
    if args.clone_all:
        print('Cloning all repos even if that step is not selected')
    else:
        print('Cloning only needed repos')

    if args.clone_all  or  'llvm' in args.steps  or  'runtimes' in args.steps:
        print('Clone from llvm repo')

    if args.clone_all or 'devfiles' in args.steps:
        print('Clone from pic32-device-file-maker repo')

    if args.clone_all or 'cmsis' in args.steps:
        print('Clone from cmsis repo')

    print('----------')


# This is true when this file is executed as a script rather than imported into another file. We
# probably don't need this, but there's no harm in checking.
if '__main__' == __name__:
    if ' ' in str(THIS_FILE_DIR):
        print('This script cannot be run from a path with spaces in it.')
        print('Doing so will mess up some paths that get passed to CMake.')
        print('Run this script from a path with no spaces.')
        exit(0)


    # The Windows Terminal (the one with tabs) supports ANSI escape codes, but the old console
    # (conhost.exe) does not unless the following weird workaround is done. This came from
    # https://bugs.python.org/issue30075.
    if is_windows():
        subprocess.call('', shell=True)

    args = get_command_line_arguments()
    process_command_line_arguments(args)
    print_arg_info(args)


    if 'clone' in args.steps:
        clone_selected_repos_from_git(args)

    if 'llvm' in args.steps:
        if args.single_stage:
            build_single_stage_llvm(args)
        else:
            build_two_stage_llvm(args)

    build_variants: list[TargetVariant] = pic32_target_variants.create_build_variants()

    if 'runtimes' in args.steps:
        for variant in build_variants:
            build_llvm_runtimes(args, variant)

    if 'devfiles' in args.steps:
        build_device_files(args)

    if 'cmsis' in args.steps:
        copy_cmsis_files()

    if 'startup' in args.steps:
        build_device_startup_files()

    # Do this extra print because otherwise the info string will be below where the command prompt
    # re-appears after this ends.
    print('\n')
