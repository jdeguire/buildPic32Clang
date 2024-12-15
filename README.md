# buildPic32Clang
A Python script to build Clang for PIC32 and SAM devices along with any supporting libraries.

Right now, this supports only Arm Cortex-M devices, like most of the SAM and all of the PIC32C
devices. MIPS and Cortex-A devices could be added in the future, but I don't have any immediate
plans for that. MIPS is basically dead (even MIPS the company designs only RISC-V chips now) and
I don't know enough about the Cortex-A parts to set them up properly.

## Requirements
Here's a quick list of what you need.

- Python 3.10 or newer
- A recent C++ compiler (MSVC, Clang, and GCC should all work)
- CMake
- GNU Make
- Ninja
- Git

On Windows you should use the Windows Terminal app instead of the old command-line interface
(conhost.exe). This script uses ASCII control codes to provide a running status of what the script
is doing and the old console does not support those very well. There are Windows installers for all
of these apps. If you need a compiler, you can use an LLVM release from 
https://github.com/llvm/llvm-project/releases.

On Linux distributions, you should be able to get everything you need from your package manager.
Your Python version might be a little old, but it may still work if it isn't too far behind 3.10.
Something like Python 3.8 might be okay. If you're using a Debian or similar distribution--say
Ubuntu or PopOS--you can get the `build-essential` package for a toolchain and probably GNU Make. 

Mac OS users are unfortunately on their own since I don't currently own a Mac.

So far, this script has been run only under the Windows Subsytem for Linux (WSL) on Windows 10. The
intent is for it to also support running on a Windows terminal as well, but that has not yet been
tested very much.

## How to Run
For now, this script can be run by opening up a terminal interface and running `./buildPic32Clang.py`
(Unix/Linux/WSL/etc.) or `python3 .\buildPic32Clang.py` (Windows). If you supply no arguments when
running it, a usable set of defaults will be used that will try to clone and build all of the projects
this script can handle.

Here are the command-line arguments you can supply to control how the script runs.

- `--help` or `-h`  
    Print a brief summary of these arguments and then exit.
- `--steps {[clone, llvm, musl, runtimes, devfiles, cmsis, all]}`  
    Select what this script should build and if it should clone the git repo for the selected 
    componenets first. Any combination of options works as long as at least one is provided. Use
    "all" to clone and build everything, which is the default.

    - **clone**: Clone the needed git repos before building. The default is to clone only what is
    needed based on the other steps selected. Add the `--clone-all` argument to clone everything.
    - **llvm**: Build LLVM, Clang, and supporting tools.
    - **musl**: Build the Musl C library for all supported device variants. A variant is a set of
    target options like whether it is ARMv6-M vs ARMv7-M or whether or not is has an FPU.
    - **runtimes**: Build libc++, Compiler-RT, and other runtime libraries for all supported device
    variants.
    - **devfiles**: Generate device-specific files like linker scripts, header files, and so on.
    - **cmsis**: Copy the Arm CMSIS files to their proper locations.
    - **all**: Do all of the above. This is the default.
- `--packs-dir DIR`  
    Indicate where the this script can find the Microchip packs used to provide information about
    supported devices. This is used only if the `devfiles` step is active. If that step is active
    and this option is not provided, the script will pop up a dialog box asking you where the
    packs directory is located. See the README in the `pic32-device-file-maker` project for more
    info: https://github.com/jdeguire/pic32-device-file-maker.
- `--llvm-build-type Release|Debug|RelWithDebInfo|MinSizeRel`  
    Select the CMake build type to use for LLVM. You can pick only one. The default is "Release".
- `--llvm-branch REF`  
    Set the LLVM git branch or tag to clone from or use "main" to get the latest sources. The
    default will be the most recent released version when the script was last updated. You can use
    the built-in help (`--help`) to see the default.
- `--cmsis-branch REF`  
    Set the CMSIS git branch or tag to clone from or use "main" to get the latest sources. The
    default will be the most recent released version when the script was last updated. You can use
    the built-in help (`--help`) to see the default.
- `--clone-all`  
    Clone every git repo even when not all of them are needed to complete the steps provided with
    `--steps`. Use `--steps clone --clone-all` to create an archive of the sources for later use.
- `--full-clone`  
    Clone the full histories of the git repos accessed by this script. This can be useful for
    development or if you want to archive the fully history of repositories. The default is to do
    only shallow clones such that no prior history is cloned.
- `--enable-lto`  
    Enable Link Time Optimization when building LLVM. The default is to have LTO disabled.
- `--single-stage`  
    Do a single-stage LLVM build. This is much quicker than the default two-stage build and so is
    useful for development. A two-stage build is normally recommended so that the distributed
    toolchain is always built with the latest tools. This can also help ensure the same behavior
    across platforms if you plan on distributing a toolchain on, say, Linux and Windows.
- `--compile-jobs`  
    Set the number of parallel compile processes to run when building any of the tools and when
    creating the device files. The default is 0, which will use one process per CPU. One per CPU is
    also the maximum allowed.
- `--link-jobs`  
    Set the number of parallel link processes to run when building any of the tools. LLVM docs
    recommend one process per 15GB of memory available. The default is 0, which will use one
    process per CPU. One per CPU is also the maximum allowed.
- `--version`  
    Print the script's version info and then exit.


## About the pic32Clang Projects
All of these projects with "pic32Clang" in the name are here to provide you a modern Clang-based
toolchain that can be used for Microchip Technology's PIC32 and SAM lines of 32-bit microcontrollers
and microprocessors (not yet, but one day). This is meant as an alternative to the XC32 toolchain
that Microchip themselves provide that supports the latest C and C++ standards and tools (such as
Clang Tidy). This toolchains is not going to be 100% compatible with XC32 because it has things
specific to the Microchip devices, but effort was made to at least allow not-too-terrible migration
from one to the other. For example, most device register names should be the same between the two
toolchains, but setting device configuration registers is different.

Use pic32Clang if you want to be able to use the latest goodies that modern C and C++ standards have
to offer on your Microchip device and you are willing to do some work and take some risk in doing so.
Use XC32 if you're looking for a seemless out-of-the-box experience that is ready to go with the
rest of Microchip's tools, such as the MPLAB X IDE and the Harmony Framework. XC32 also comes with
support from people who actually know what they're doing whereas I'm just some random dude on the
internet 😉.

There currently isn't a fully-working IDE plugin to use Clang with MPLAB X or the MPLAB VS Code
Extensions. I do have a an MPLAB X plugin called `toolchainPic32Clang` that you are welcome to try,
but I have not worked on it for a long time and it is basically deprecated at this point. You can
find it at https://github.com/jdeguire/toolchainPic32Clang if you want to play around with it. My
intent is to figure out how to integrate this with the MPLAB VS Code Extensions, which at this time
is in early beta but is slated to replace MPLAB X.

## License
See the LICENSE file for the full thing, but basically this is licensed using the BSD 3-clause
license because I don't know anything about licenses and that one seemed good.

The CMake cache files located under "cmake_caches" are licensed under the modified Apache 2.0
license used by Clang. Those files started out as copies of exmaple CMake files from the Clang
source and so presumably they must comply with Clang's license. Again, I know nothing about
licenses, so this also seems good. 
