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
# pic32_target_variants.py
#
# This file contains data structures that capture the target variants we need to build for all of
# the PIC32 and SAM devices we need to support. For example, there would be different variants for
# ARMv6-M vs ARMv7-M and so on, or for devices with and without FPUs. This file is used in the
# main buildPic32Clang.py script and there really isn't a good reason to use this script directly.
# I moved the target variant stuff in here mostly to reduce some clutter in the main script.
#

from dataclasses import dataclass
from pathlib import Path
import subprocess

# Notes:
# -- Devices for which the datasheet claims as MIPS32r5 also have an FPU and vice versa. These are 
#    the PIC32MZ EF and PIC32MK devices. All other devices with no FPU are assumed to be MIPS32r2.
# -- Devices with an FPU also have the DSPr2 extension, but not vice versa. The PIC32MZ DA and
#    PIC32MZ EC have DSPr2, but not an FPU.
# -- The previous note implies that all MIPS32r5 devices have the DSPr2 extension.
# -- Only the PIC32MX series uses the older MIPS16 extension; none of them have an FPU or DSP ASE.
# -- It's not clear if Clang/LLVM cares about r2 vs r5 (it might only care about r6 vs rest).
# -- MIPS16 is commented out for now because LLVM does not properly support MIPS16.
# -- The M0, M0+, M23, and M3 do not have an FPU.
# -- The M4 has a 32-bit FPU; the M7 has a 64-bit FPU. These are Armv7em.
# -- Devices with MVE (M-profile Vector Extensions) use the hard float ABI even if they do not have
#    a normal FPU. MVE registers are remapped FPU registers.
# -- The A5 can have either a normal 64-bit FPU or one with NEON. This is Armv7a.
# -- The M series is always Thumb, so we do not have to differentiate.
@dataclass(frozen=True)
class TargetVariant:
    series : str
    triple : str
    path : Path
    options : list[str]

@dataclass(frozen=True)
class Mips32Variant(TargetVariant):
    def __init__(self, multilib_path: Path, arch: str, options: list[str]) -> None:
        # '-G0' prevents libraries from putting small globals into the small data sections. This
        # is the safest option since an application can control the size threshold with '-G<size>'.
#        common_opts = ['-target', 'mipsel-linux-gnu', f'-march={arch}', '-G0', '-fomit-frame-pointer']
        common_opts = [f'-march={arch}', '-G0', '-fomit-frame-pointer']

        return super().__init__('mips32', 'mipsel-linux-gnu', multilib_path, common_opts + options)

@dataclass(frozen=True)
class CortexMVariant(TargetVariant):
    def __init__(self, multilib_path: Path, arch: str, options: list[str]) -> None:
        # The '-mimplicit-it' flag was needed for Musl. Whatever options I used for Musl caused its
        # configure script to not pick that up automatically.
        # TODO: This may not be needed anymore since we are no longer using Musl.
#        common_opts = ['-target', 'arm-none-eabi', f'-march={arch}', '-mimplicit-it=always', '-fomit-frame-pointer']
        common_opts = [f'-march={arch}', '-mimplicit-it=always', '-fomit-frame-pointer']

        # The CMake files for one of the LLVM runtime libaries (maybe Compiler-RT?) looks for the 
        # architecture in the target triple. We do not need extensions ("+foo") to be specified.
        triple = f'{arch.split('+')[0]}-none-eabi'

        return super().__init__('cortex-m', triple, multilib_path, common_opts + options)

@dataclass(frozen=True)
class CortexAVariant(TargetVariant):
    def __init__(self, multilib_path: Path, arch: str, options: list[str]) -> None:
        # The '-mimplicit-it' flag was needed for Musl. Whatever options I used for Musl caused its
        # configure script to not pick that up automatically.
        # TODO: This may not be needed anymore since we are no longer using Musl.
#        common_opts = ['-target', 'arm-none-eabi', f'-march={arch}', '-mimplicit-it=always', '-fomit-frame-pointer']
        common_opts = [f'-march={arch}', '-mimplicit-it=always', '-fomit-frame-pointer']

        # The CMake files for one of the LLVM runtime libaries (maybe Compiler-RT?) looks for the 
        # architecture in the target triple. We do not need extensions ("+foo") to be specified.
        triple = f'{arch.split('+')[0]}-none-eabi'

        return super().__init__('cortex-a', triple, multilib_path, common_opts + options)


# The paths here are set up to match paths provided by the multilib.yaml file generated by the
# 'pic32-device-file-maker' project. If you need to change them here, then you'll need to change
# them in that project, too. The YAML file is in the "premade" directory in that project.
#
# For ARM chips, you can find the architecture name pretty easily by looking up the CPU name 
# (ex: "Cortex-M7") online. Wikipedia has a page for Cortex-M with tables to show the architecture.
# Like you see here, the compiler takes the architecture name in lower case and without dashes.
# 
# Finding the FPU name can be tricky. Your best bet is to find the "Cortex-M__ Technical Reference
# Manual" and look up the FPU info in there. That will tell you if the FPU can support half-,
# single-, or double-precision math and the FPU version (ex: "FPv5"). Some CPUs can optionally
# choose from multiple FPU implementations. The Technical Reference Manual may also refer you to an
# Architecture Reference Manual for more info.
#
# The best way I've found for seeing what you can pass to the compiler is to look in LLVM's source
# code. The file "llvm/llvm/include/llvm/TargetParser/ARMTargetParser.def" has a list of FPU and CPU
# names you can use to figure out the name of the FPU for your device.
TARGETS: list[TargetVariant] = [
    ## MIPS
    # Mips32Variant(Path('r2/nofp'),
    #               'mips32r2',
    #               ['-msoft-float']),
    # Mips32Variant(Path('r2/mips16/nofp'),
    #               'mips32r2',
    #               ['-mips16', '-msoft-float']),
    # Mips32Variant(Path('r2/micromips/nofp'),
    #               'mips32r2',
    #               ['-mmicromips', '-msoft-float']),
    # Mips32Variant(Path('r2/micromips/dspr2/nofp'),
    #               'mips32r2',
    #               ['-mmicromips', '-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r2/dspr2/nofp'),
    #               'mips32r2',
    #               ['-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r5/dspr2/nofp'),
    #               'mips32r2',
    #               ['-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r5/dspr2/fpu64'),
    #               'mips32r5',
    #               ['-mdspr2', '-mhard-float', '-mfp64']),
    # Mips32Variant(Path('r5/micromips/dspr2/nofp'),
    #               'mips32r5',
    #               ['-mmicromips', '-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r5/micromips/dspr2/fpu64'),
    #               'mips32r5',
    #               ['-mmicromips', '-mdspr2', '-mhard-float', '-mfp64']),

    ## Armv6m
    CortexMVariant(Path('v6m/nofp'),
                   'armv6m',
                   ['-mfpu=none', '-mfloat-abi=soft']),

    ## Armv7m
    CortexMVariant(Path('v7m/nofp'),
                   'armv7m',
                   ['-mfpu=none', '-mfloat-abi=soft']),

    ## Armv7em
    CortexMVariant(Path('v7em/nofp'),
                   'armv7em',
                   ['-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v7em/fpv4-sp-d16'),
                   'armv7em',
                   ['-mfpu=fpv4-sp-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v7em/fpv5-sp-d16'),
                   'armv7em',
                   ['-mfpu=fpv5-sp-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v7em/fpv5-d16'),
                   'armv7em',
                   ['-mfpu=fpv5-d16', '-mfloat-abi=hard']),

    ## Armv8m.base
    CortexMVariant(Path('v8m.base/nofp'),
                   'armv8m.base',
                   ['-mfpu=none', '-mfloat-abi=soft']),

    ## Armv8m.main
    CortexMVariant(Path('v8m.main/nofp'),
                   'armv8m.main',
                   ['-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v8m.main/fpv5-sp-d16'),
                   'armv8m.main',
                   ['-mfpu=fpv5-sp-d16', '-mfloat-abi=hard']),

    ## Armv8.1m.main
    CortexMVariant(Path('v8.1m.main/nofp/nomve'),
                   'armv8.1m.main',
                   ['-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v8.1m.main/nofp/mve'),
                   'armv8.1m.main+mve',
                   ['-mfpu=none', '-mfloat-abi=hard']),     # MVE needs hard ABI
    CortexMVariant(Path('v8.1m.main/fp-armv8-fullfp16-sp-d16/nomve'),
                   'armv8.1m.main',
                   ['-mfpu=fp-armv8-fullfp16-sp-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v8.1m.main/fp-armv8-fullfp16-sp-d16/mve'),
                   'armv8.1m.main+mve.fp',
                   ['-mfpu=fp-armv8-fullfp16-sp-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v8.1m.main/fp-armv8-fullfp16-d16/nomve'),
                   'armv8.1m.main',
                   ['-mfpu=fp-armv8-fullfp16-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v8.1m.main/fp-armv8-fullfp16-d16/mve'),
                   'armv8.1m.main+mve.fp+fp.dp',
                   ['-mfpu=fp-armv8-fullfp16-d16', '-mfloat-abi=hard']),

    ## Armv7a
    # CortexAVariant(Path('v7a/nofp'),
    #                'armv7a',
    #                ['-mfpu=none', '-mfloat-abi=soft']),
    # CortexAVariant(Path('v7a/vfpv4-d16'),
    #                'armv7a',
    #                ['-mfpu=vfpv4-d16', '-mfloat-abi=hard']),
    # CortexAVariant(Path('v7a/neon-vfpv4'),
    #                'armv7a',
    #                ['-mfpu=neon-vfpv4', '-mfloat-abi=hard']),
    # CortexAVariant(Path('v7a/thumb/nofp'),
    #                'armv7a',
    #                ['-mthumb', '-mfpu=none', '-mfloat-abi=soft']),
    # CortexAVariant(Path('v7a/thumb/vfpv4-d16'),
    #                'armv7a',
    #                ['-mthumb', '-mfpu=vfpv4-d16', '-mfloat-abi=hard']),
    # CortexAVariant(Path('v7a/thumb/neon-vfpv4'),
    #                'armv7a',
    #                ['-mthumb', '-mfpu=neon-vfpv4', '-mfloat-abi=hard']),
]

def get_multilib_flags_from_clang(variant: TargetVariant, clang_path: Path) -> list[str]:
    '''Query Clang for a set of flags used to determine which multilib variant it will use when
    linking.

    There are multiple ways to tell Clang about your device. For example "-target armv6m-none-eabi"
    and "-target arm-none-eabi -march=armv6m" are equivalent. To handle this, Clang creates a
    normalized set of flags it will use to select the multilibs. We need to know what these normalized
    flags are, so Clang provides a way to query them.
    '''
    # As of Clang 20, the option to get the flags is "-print-multi-flags-experiemental'. If you are
    # running a newer version and that option does not appear to work, then remove the "-experimental"
    # part and try again.
    cmd = [clang_path.as_posix(),
           '-target', variant.triple,
           '-print-multi-flags-experimental']
    cmd += variant.options
    print(' '.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, timeout=5.0, check=True, text=True, encoding='utf-8')

    return proc.stdout.split()


def create_build_variants() -> list[TargetVariant]:
    '''Create a list of build variants that are used to build supporting libraries for the toolchain.
    
    This uses the list of targets above and creates new versions that vary by the optimization options
    to be used. Each target in the list above will therefore have several versions that differ by
    the optimization options used to build them. Each optimization variant also has its own path.
    '''
    # Clang's multilib support looks for architecture options (like --target and -march),
    # -f(no-)rtti, and -f(no-)exceptions. It cannot differentiate based on other options, like
    # optimization levels. For now, we'll specify options in the "pic32clang-target-runtimes.cmake"
    # file based on the selected CMake build type. We might need to handle the -fexceptions and
    # -frtti options in the future.

    # print("****BUILDING REDUCED VARIANTS FOR DEBUGGING****")
    return TARGETS
