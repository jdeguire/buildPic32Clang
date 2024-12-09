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
# -- The M0, M0+, M23, and M3 do not have an FPU.
# -- The M4 has a 32-bit FPU; the M7 has a 64-bit FPU. These are Armv7em.
# -- The A5 can have either a normal 64-bit FPU or one with NEON. This is Armv7a.
# -- The M series is always Thumb, so we do not have to differentiate.
@dataclass(frozen=True)
class TargetVariant:
    arch : str
    triple : str
    path : Path
    subarch : str
    options : list[str]

@dataclass(frozen=True)
class Mips32Variant(TargetVariant):
    def __init__(self, multilib_path: Path, subarch: str, options: list[str]) -> None:
        # '-G0' prevents libraries from putting small globals into the small data sections. This
        # is the safest option since an application can control the size threshold with '-G<size>'.
        common_opts = ['-target', 'mipsel-linux-gnu', '-G0', '-fomit-frame-pointer']
        all_opts = common_opts + options

        return super().__init__('mips32', 'mipsel-linux-gnu', multilib_path, subarch, all_opts)

@dataclass(frozen=True)
class CortexMVariant(TargetVariant):
    def __init__(self, multilib_path: Path, subarch: str, options: list[str]) -> None:
        # The '-mimplicit-it' flag is needed for Musl. Whatever options I'm passing are causing the
        # Musl configure script to not pick that up automatically.
        common_opts = ['-target', 'arm-none-eabi', '-mimplicit-it=always', '-fomit-frame-pointer']
        all_opts = common_opts + options

        return super().__init__('cortex-m', 'arm-none-eabi', multilib_path, subarch, all_opts)

@dataclass(frozen=True)
class CortexAVariant(TargetVariant):
    def __init__(self, multilib_path: Path, subarch: str, options: list[str]) -> None:
        # The '-mimplicit-it' flag is needed for Musl. Whatever options I'm passing are causing the
        # Musl configure script to not pick that up automatically.
        common_opts = ['-target', 'arm-none-eabi', '-mimplicit-it=always', '-fomit-frame-pointer']
        all_opts = common_opts + options

        return super().__init__('cortex-a', 'arm-none-eabi', multilib_path, subarch, all_opts)


# The paths here are set up to match paths provided by the multilib.yaml file generated by the
# 'pic32-device-file-maker' project. If you need to change them here, then you'll need to change
# them in that project, too. The YAML file is in the "premade" directory in that project.
TARGETS = [
    # Mips32Variant(Path('r2/nofp'),
    #               'mips32r2',
    #               ['-march=mips32r2', '-msoft-float']),
    # Mips32Variant(Path('r2/mips16/nofp'),
    #               'mips32r2',
    #               ['-march=mips32r2', '-mips16', '-msoft-float']),
    # Mips32Variant(Path('r2/micromips/nofp'),
    #               'mips32r2',
    #               ['-march=mips32r2', '-mmicromips', '-msoft-float']),
    # Mips32Variant(Path('r2/micromips/dspr2/nofp'),
    #               'mips32r2',
    #               ['-march=mips32r2', '-mmicromips', '-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r2/dspr2/nofp'),
    #               'mips32r2',
    #               ['-march=mips32r2', '-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r5/dspr2/nofp'),
    #               'mips32r2',
    #               ['-march=mips32r5', '-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r5/dspr2/fpu64'),
    #               'mips32r5',
    #               ['-march=mips32r5', '-mdspr2', '-mhard-float', '-mfp64']),
    # Mips32Variant(Path('r5/micromips/dspr2/nofp'),
    #               'mips32r5',
    #               ['-march=mips32r5', '-mmicromips', '-mdspr2', '-msoft-float']),
    # Mips32Variant(Path('r5/micromips/dspr2/fpu64'),
    #               'mips32r5',
    #               ['-march=mips32r5', '-mmicromips', '-mdspr2', '-mhard-float', '-mfp64']),

    CortexMVariant(Path('v6m/nofp'),
                   'armv6m',
                   ['-march=armv6m', '-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v7m/nofp'),
                   'armv7m',
                   ['-march=armv7m', '-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v7em/nofp'),
                   'armv7em',
                   ['-march=armv7em', '-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v7em/fpv4-sp-d16'),
                   'armv7em',
                   ['-march=armv7em', '-mfpu=fpv4-sp-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v7em/fpv5-d16'),
                   'armv7em',
                   ['-march=armv7em', '-mfpu=fpv5-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v8m.base/nofp'),
                   'armv8m.base',
                   ['-march=armv8m.base', '-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v8m.main/nofp'),
                   'armv8m.main',
                   ['-march=armv8m.main', '-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v8m.main/fpv5-sp-d16'),
                   'armv8m.main',
                   ['-march=armv8m.main', '-mfpu=fpv5-sp-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v8.1m.main/nofp/nomve'),
                   'armv8.1m.main',
                   ['-march=armv8.1m.main', '-mfpu=none', '-mfloat-abi=soft']),
    CortexMVariant(Path('v8.1m.main/nofp/mve'),
                   'armv8.1m.main+mve',
                   ['-march=armv8.1m.main+mve', '-mfpu=none', '-mfloat-abi=hard']), # MVE needs hard ABI
    CortexMVariant(Path('v8.1m.main/fp-armv8-fullfp16-d16/nomve'),
                   'armv8.1m.main',
                   ['-march=armv8.1m.main', '-mfpu=fp-armv8-fullfp16-d16', '-mfloat-abi=hard']),
    CortexMVariant(Path('v8.1m.main/fp-armv8-fullfp16-d16/mve'),
                   'armv8.1m.main+mve.fp+fp.dp',
                   ['-march=armv8.1m.main+mve.fp+fp.dp', '-mfpu=fp-armv8-fullfp16-d16', '-mfloat-abi=hard']),

    # CortexAVariant(Path('v7a/nofp'),
    #                'armv7a',
    #                ['-march=armv7a', '-mfpu=none', '-mfloat-abi=soft']),
    # CortexAVariant(Path('v7a/vfpv4-d16'),
    #                'armv7a',
    #                ['-march=armv7a', '-mfpu=vfpv4-d16', '-mfloat-abi=hard']),
    # CortexAVariant(Path('v7a/neon-vfpv4'),
    #                'armv7a',
    #                ['-march=armv7a', '-mfpu=neon-vfpv4', '-mfloat-abi=hard']),
    # CortexAVariant(Path('v7a/thumb/nofp'),
    #                'armv7a',
    #                 ['-march=armv7a', '-mthumb', '-mfpu=none', '-mfloat-abi=soft']),
    # CortexAVariant(Path('v7a/thumb/vfpv4-d16'),
    #                'armv7a',
    #                ['-march=armv7a', '-mthumb', '-mfpu=vfpv4-d16', '-mfloat-abi=hard']),
    # CortexAVariant(Path('v7a/thumb/neon-vfpv4'),
    #                'armv7a',
    #                ['-march=armv7a', '-mthumb', '-mfpu=neon-vfpv4', '-mfloat-abi=hard']),
    ]

def create_build_variants() -> list[TargetVariant]:
    '''Create a list of build variants that are used to build supporting libraries for the toolchain.
    
    This uses the list of targets above and creates new versions that vary by the optimization options
    to be used. Each target in the list above will therefore have several versions that differ by
    the optimization options used to build them. Each optimization variant also has its own path.
    '''
    variants: list[TargetVariant] = []
    # opts = [(Path('.'),  ['-O0']),
    #         (Path('o1'), ['-O1']),
    #         (Path('o2'), ['-O2']),
    #         (Path('o3'), ['-O3']),
    #         (Path('os'), ['-Os']),
    #         (Path('oz'), ['-Oz'])]
    
    # Clang's multilib support looks for architecture options (like --target and -march),
    # -f(no-)rtti, and -f(no-)exceptions. It cannot differentiate based on other options, like
    # optimization levels. For now, just use -O2. We might need to handle the -fexceptions and
    # -frtti options in the future.
    opts = [(Path('.'), ['-O2'])]

    for target in TARGETS:
        for opt in opts:
            variant_path = target.path / opt[0]
            variant_options = target.options + opt[1]
            variants.append(TargetVariant(target.arch, target.triple, variant_path, 
                                          target.subarch, variant_options))

    return variants
