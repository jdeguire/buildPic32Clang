# buildPic32Clang
A Python script to build Clang for PIC32 and SAM devices along with any supporting libraries.

Right now, this supports only Arm Cortex-M devices, like most of the SAM and all of the PIC32C
devices. MIPS and Cortex-A devices could be added in the future, but I don't have any immediate
plans for that. MIPS is basically dead (even MIPS the company designs only RISC-V chips now) and
I don't know enough about the Cortex-A parts to set them up properly.


## Requirements
Here's a quick list of what you need.

- Python 3.10 or newer
- A recent C++ compiler (MSVC on Windows; Clang or GCC otherwise)
- CMake
- Ninja
- Git

### Windows
You can find installers for all of the above apps for Windows. You will need to add CMake and Ninja
to your PATH. I cheated and just put `ninja.exe` into the same directory as `cmake.exe`. For a
compiler, you can go grab the latest Visual Studio Build Tools from https://visualstudio.microsoft.com/downloads/.
In the installer, select "Desktop development with C++" then on the right side add a checkbox to
"C++ ATL for latest vNNN build tools".

If you install Python using the installer from the Python website, you need to make sure your PATH
is updated. There is a little checkbox early on in the installer that is easy to miss to do that.
You might also see an option to install "tcl/tk" or something like that. You want that selected. If
you install Python from the Windows Store, then these should be handled for you.

Once you install Python, you'll need to install a couple of packages using Python's package manager.
You need `pyyaml` at minimum. You can get it with `pip3 install pyyaml`. If you want to build the
documentation, then you'll also need to run `pip3 install sphinx sphinx-reredirects myst-parser`.
You might see warnings about scripts not being in your PATH if you are using the Windows Store
version of Python. You will probably want to add those to your PATH or use the install from the
Python website.

You should install and use the Windows Terminal app. This script uses ASCII control codes to
provide a running status of what the script is doing and the old console does not support those
very well. This should still run in the old console app, but the output might look off.

### Linux
On Linux distributions, you should be able to get everything you need from your package manager.
Your Python version might be a little old, but it may still work if it isn't too far behind 3.10.
Something like Python 3.8 might be okay. If you're using a Debian or similar distribution--say
Ubuntu or PopOS--you can get the `build-essential` package for a toolchain.

For Python, You may need to install `tkinter` from your system's package manager. The name of the 
package will vary based on your distribution, but will likely be something like `python3-tk` or
`python3-tkinter`. You cannot install this from `pip`, Python's package manager.

You'll also need to install `pyyaml`. Try running `pip install pyyaml` to do that. If you get a message
about your environment being "externally managed", then you'll need to use your system's package
manager instead. The package name may vary from distro to distro, but on Ubuntu you need the
`python3-yaml` package. If you also want to build the documentation, you'll also need the `sphinx`,
`sphinx-reredirects`, and the `myst-parser` packages. Again, whether you can use `pip` or your system
package manager will depend on your system.

If your distro uses `python3` but does not include `python`, then you will need to fix that. On Debian
and its derivatives like Ubuntu, you can install the `python-is-python3` package. Otherwise, you can
create an alias or symbolic link to map `python` to `python3`.

### Mac OS
Mac OS users are unfortunately on their own since I don't currently own a Mac.


## How to Run
For now, this script can be run by opening up a terminal interface and running `./buildPic32Clang.py`
(Unix/Linux/WSL/etc.) or `python3 .\buildPic32Clang.py` (any of those + Windows). On Linux or Unix
you might need to run `chmod +x ./buildPic32Clang.py` once before you run it for the first time.
If you supply no arguments when running it, a usable set of defaults will be used that will try to
clone and build all of the projects this script can handle.

On Windows, you will likely need to run this script from either the "Developer Command Prompt for
VS 20xx" or the "Developer PowerShell for VS 20xx" if you need to build the toolchain. Do not run
this script from a long path. If you get error code RC1109 from `rc.exe` when building LLVM, then
you need to run the script from a shorter path.

Do not run this script from a path with space in it. Doing so can mess up paths provided to CMake,
so this script will check for that and tell you to move it if the path has spaces. I tried to use
relative paths where possible to avoid this, but there are a few places I couldn't figure out.

Here are the command-line arguments you can supply to control how the script runs.

- `--help` or `-h`  
    Print a brief summary of these arguments and then exit.
- `--steps {[clone, llvm, runtimes, devfiles, cmsis, startup, package, all]}`  
    Select what this script should build and if it should clone the git repo for the selected 
    componenets first. Any combination of options works as long as at least one is provided. Use
    "all" to clone and build everything, which is the default.

    - **clone**: Clone the needed git repos before building. The default is to clone only what is
    needed based on the other steps selected. Add the `--clone-all` argument to clone everything.
    - **llvm**: Build LLVM, Clang, and supporting tools.
    - **runtimes**: Build llvm-libc, libc++, Compiler-RT, and other runtime libraries for all
    supported device variants.
    - **devfiles**: Generate device-specific files like linker scripts, header files, and so on.
    - **cmsis**: Copy the Arm CMSIS files to their proper locations.
    - **startup**: Build the startup code for the devices with this toolchain. The other steps must
    either be specified as well or completed in a previous run.
    - **package**: Package all of the toolchain files into an archive for distribution. The archive
    will be a `.zip` on Windows and a `.tar.bz2` everywhere else. The top level directory in the
    archive will contain the Pic32Clang version, so that multiple versions can easily exist together
    on a system. The archive will be located in the "pic32clang" directory.
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
- `--skip-existing`  
    Set this to skip clones of repos that already exist in the working area instead of raising an
    exception.
- `--enable-lto`  
    Enable Link Time Optimization when building LLVM. The default is to have LTO disabled.
- `--single-stage`  
    Do a single-stage LLVM build. This is much quicker than the default two-stage build and so is
    useful for development. A two-stage build is normally recommended so that the distributed
    toolchain is always built with the latest tools. This can also help ensure the same behavior
    across platforms if you plan on distributing a toolchain on, say, Linux and Windows.
- `--build-docs`  
    Also build documentation when building LLVM and the runtimes. Documents are generated in HTML
    and Unix Manpage formats for LLVM, Clang, and other tools. Only HTML is currently available for
    the runtimes. You need extra packages to build documentation; see above for what you need.
- `--compile-jobs`  
    Set the number of parallel compile processes to run when building any of the tools and when
    creating the device files. The default is 0, which will use one process per CPU. One per CPU is
    also the maximum allowed.
- `--link-jobs`  
    Set the number of parallel link processes to run when building the LLVM tools. LLVM docs
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
find it at https://github.com/jdeguire/toolchainPic32Clang if you want to play around with it. I
do not know if the MPLAB VS Code Extensions will be extendable to support non-Microchip toolchains.
As of this writing, the VS Code Extensions are considered early access quality and so they are still
under very heavy development.


## License
See the LICENSE file for the full thing, but basically this is licensed using the BSD 3-clause
license because I don't know anything about licenses and that one seemed good.

The CMake cache files located under "cmake_caches" are licensed under the modified Apache 2.0
license used by Clang. Those files started out as copies of exmaple CMake files from the Clang
source and so presumably they must comply with Clang's license. Again, I know nothing about
licenses, so this also seems good. 

## Trademarks
This project and the similarly-named ones make references to "PIC32", "SAM", "XC32", and "MPLAB"
products from Microchip Technology. Those names are trademarks or registered trademarks of Microchip
Technology.

These project also refer to "Arm", "ARM", "Cortex", and "CMSIS", which are all trademarks of Arm
Limited.

These projects are all independent efforts not affiliated with, endorsed, sponsored, or otherwise
approved by Microchip Technology nor Arm Limited.
