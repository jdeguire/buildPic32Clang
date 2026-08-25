# buildMchpClang
_This project used to be called "buildPic32Clang", but I changed it to avoid any trademark concerns
with using "PIC" in the name._

This is a Python script to build Clang for Microchip Technology's PIC32 and SAM devices along with
any supporting libraries.

Right now, this supports only Arm devices, like most of the SAM and all of the PIC32C devices. MIPS
devices could be added in the future, but I don't have any immediate plans for that. MIPS is
basically dead (even MIPS the company designs only RISC-V chips now), so it is unlikely to get
much love in the future. As of this writing in October 2025, there is no MIPS target maintainer
for LLVM.

LLVM does have an AVR backend now, so in theory one could extend this to support those, too.

## Requirements
Here's a quick list of what you need.

- Python 3.10 or newer
- A recent C++ compiler (MSVC on Windows; Clang or GCC otherwise)
- CMake
- Ninja
- Git

The subsections below will also list a few extra Python packages you need and how to get them.

### Windows
You can find installers for all of the above apps for Windows. You will need to add CMake and Ninja
to your PATH. I cheated and just put `ninja.exe` into the same directory as `cmake.exe`. For a
compiler, you can go grab the latest Visual Studio Build Tools from https://visualstudio.microsoft.com/downloads/.
In the installer, select "Desktop development with C++" then on the right side add a checkbox to
"C++ ATL for latest vNNN build tools".

If you install Python using the installer from the Python website, you need to make sure your PATH
is updated. There is a little checkbox early on in the installer that is easy to miss to do that.
If you install Python from the Windows Store, then this should be handled for you.

Once you install Python, you'll need to install a couple of packages using Python's package manager.
You need `pyyaml` at minimum. You can get it with `pip3 install pyyaml`. If you want to build the
documentation, then you'll also need to run `pip3 install sphinx furo sphinx-reredirects myst-parser`.
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

You'll also need to install `pyyaml`. Try running `pip install pyyaml` to do that. If you get a message
about your environment being "externally managed", then you'll need to use your system's package
manager instead. The package name may vary from distro to distro, but on Ubuntu you need the
`python3-yaml` package. If you also want to build the documentation, you'll also need the `sphinx`,
`sphinx-reredirects`, `furo`, and the `myst-parser` packages. Again, whether you can use `pip` or
your system package manager will depend on your system.

If your distro uses `python3` but does not include `python`, then you will need to fix that. On Debian
and its derivatives like Ubuntu, you can install the `python-is-python3` package. Otherwise, you can
create an alias or symbolic link to map `python` to `python3`.

### Mac OS
Mac OS users are unfortunately on their own since I don't currently own a Mac.


## A Note About Device Packs
Part of the build process for mchpClang is to generate things like header files, linker scripts,
startup code, and so on, for the many PIC and SAM devices it supports. This is done using the
`atdf-device-file-maker` project located at https://github.com/jdeguire/atdf-device-file-maker.
That project works by looking for and parsing special files that describe Microchip parts. These
files end in ".atdf" (hence the name of the project) and are distributed in bundles called "device
packs". 

This script can use the `mchp-pack-downloader` script to get packs for you from Microchip's pack
repository. You can find the downloader script at https://github.com/jdeguire/mchp-pack-downloader.
The default behavior is to check if packs have already been downloaded and use those if so. If packs
have not been downloaded, then this script will run the downloader script to get the latest versions
of the packs for the devices this toolchain supports. This script looks for the `packs/` directory
created by the downloader script to determine if packs have been already downloaded. This default
behavior occurs only if the `devfiles` build step is active. All steps are active by default.

You can force packs to be redownloaded by supplying the `--download-packs` command-line argument.
This can be handy if you want to ensure you have the latest packs or if you are creating a source
archive. You can also instead supply your own packs to use with the `--packs-dir` option.
You cannot supply both arguments at the same time and doing so will cause this script to exit with
an error telling you this.


## How to Run
Open up a terminal on your system and navigate to where the script is located. Run either
`./buildMchpClang.py` (Unix/Linux/WSL/etc.) or `python3 .\buildMchpClang.py` (Windows). On Linux or
Unix you might need to run `chmod +x ./buildMchpClang.py` once before you run it for the first time.
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
- `--steps {[clone, sources, llvm, runtimes, docs, devfiles, cmsis, startup, distribution, all]}`  
    Select what this script should build and if it should clone the git repo for the selected 
    componenets first. Any combination of options works as long as at least one is provided. Use
    "all" to clone and build everything, which is the default.

    - **clone**: Clone the needed git repos before building. The default is to clone only what is
    needed based on the other steps selected. Add the `--clone-all` argument to clone everything.
    - **sources**: Package all of the cloned and downloaded sources into a source archive before
    building anything. This will keep the sources in case you ever need to rebuild a particular
    version of this toolchain. The archive will be a `.zip` on Windows and a `.tar.bz2` everywhere
    else. The top level directory in the archive will contain the MchpClang version, so that multiple
    versions can easily exist together on a system. The archive will be located in the `mchpclang/`
    directory.
    - **llvm**: Build LLVM, Clang, and supporting tools.
    - **runtimes**: Build llvm-libc, libc++, Compiler-RT, and other runtime libraries for all
    supported device variants.
    - **docs**: Build a set of docs specific to mchpClang in HTML format. This will also build docs
    for LLVM and/or the runtimes if those steps are selected. Some LLVM docs are build in manpage
    format along with HTML.
    - **devfiles**: Generate device-specific files like linker scripts, header files, and so on.
    - **cmsis**: Copy the Arm CMSIS files to their proper locations.
    - **startup**: Build the startup code for the devices with this toolchain. The other steps must
    either be specified as well or completed in a previous run.
    - **distribution**: Package all of the toolchain binaries and supporting files into an archive
    ready for distribution. The archive will be a `.zip` on Windows and a `.tar.bz2` everywhere else.
    The top level directory in the archive will contain the MchpClang version, so that multiple versions
    can easily exist together on a system. The archive will be located in the `mchpclang/` directory.
    - **all**: Do all of the above. This is the default.
- `--skip STEPS`  
    Like the `--steps` argument but this instead removes steps. Use this when you want to do all but
    a few steps. The script processes the `--steps` argument first and then uses this one to determine
    what to remove.
- `--packs-dir DIR`  
    Provide a directory at which this script can find Microchip device packs instead of having to
    download them. This is used only if the `devfiles` step is active. Relative paths are based on
    your current working directory. This script resolves paths using Python's `Path.resolve()` 
    function. This cannot be used with the `--download-packs` option. See [above](#a-note-about-device-packs)
    for more info on packs and how this script handles them.
- `--download-packs`  
    Redownload device packs even if packs were found by this script. This is useful if you want to
    ensure you have the latest packs or if you want to create a source archive. This cannot be used
    with the `--packs-dir` option. See [above](#a-note-about-device-packs) for more info on packs
    and how this script handles them.
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
- `--devfiles-branch REF`  
    Set the device files maker git branch or tag to clone from or use "main" to get the latest sources.
    The default will be the most recent released version when the script was last updated. You can use
    the built-in help (`--help`) to see the default.
- `--docs-branch REF`  
    Set the mchpClang docs git branch or tag to clone from or use "main" to get the latest sources.
    The default will be the most recent released version when the script was last updated. You can use
    the built-in help (`--help`) to see the default.
- `--packs-dl-branch REF`  
    Set the `mchp-pack-downloader` git branch or tag to clone from or use "main" to get the latest
    sources. The default will be the most recent released version when the script was last updated.
    You can use the built-in help (`--help`) to see the default.
- `--clone-all`  
    Clone every git repo even when not all of them are needed to complete the steps provided with
    `--steps`. This can be useful for creating a source archive. See the examples below for how to
    do that.
- `--full-clone`  
    Clone the full histories of the git repos accessed by this script. This can be useful for
    development or if you want to archive the full history of repositories. The default is to do
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
- `--compile-jobs`  
    Set the number of parallel compile processes to run when building any of the tools and when
    creating the device files. The default is 0, which will use one process per CPU. Two per CPU
    is the maximum allowed.
- `--link-jobs`  
    Set the number of parallel link processes to run when building the LLVM tools. The default is 1,
    which will perform one link at a time. You can increase this if you have plenty of CPU cores and
    RAM. LLVM docs recommend one process per 15GB of memory available. The max is two per CPU, but
    you probably do not want to do that.
- `--version`  
    Print the script's version info and then exit.


## Run Examples
Here are a few example commands you can run. You should navigate your terminal to the location in
which this script is located. Remember that on Linux you might need to use `chmod +x ./buildMchpClang.py`
to make this script runnable.

**Standard Build**  
If you are running this script for the very first time, then you can start by running it with no
arguments. If you have run this before and want to ensure you clone the proper set of sources, then
delete the `mchpclang/` subdirectory if it exists. This is particularly important if you updated this
script so that you can get the proper tool versions.

```
# Linux/Unix
./buildMchpClang.py

# Windows
python3 .\buildMchpClang.py
```

This will apply useful defaults, which will clone all of the needed repos from Git and build them all
in Release mode. This will also download device packs for you if needed. Finally, this will build
documentation for LLVM, the runtime libraries, and for mchpClang itself. All of the sources and the
final installation will be compressed into two archives that will be located in the `mchpclang/`
subdirectory generated by this script.

The script clones tags of the repositories that corresponding to releases that were recent as of the
last time this script was updated. Use the `--XXX-branch` options described above to pick a particular
tag or branch.

If you get an error saying that you are trying to clone repositories that already exist, you can
delete those repos (or just delete the whole `mchpclang/` subdirectory) and try again. You can also
use the `--skip-existing` option to ignore existing repositories and continue on. That option can be
useful if you have already run the script once and need to run it again without re-cloning repos.

Have a look at the options above to see what else you can add.

**Making a Source Archive**  
You may want to download the sources and archive them for later. This is especially useful if you
need to track versions of this toolchain that you have used to build your projects. Use this command
to clone the needed repositories without building anything.

```
# Linux/Unix
./buildMchpClang.py --steps clone sources --clone-all --download-packs

# Windows
python3 .\buildMchpClang.py --steps clone sources --clone-all --download-packs
```

This will clone the source files you need to build that version of toolchain in the future and pack
them into an archive. This will also download the latest versions of device packs for the devices
this toolchain supports and add those to the archive. The archive will be located in the `mchpclang/`
subdirectory generated by this script.

**Building From a Source Archive**  
If you previously ran the above command and now have an archive of the sources, extract the contents
of the archive and navigate your console to the `buildMchpClang.py` script in the new directory.
Having your terminal's "working directory" be the script's location is particularly important when
you are building from an archive. You can use the following command to build the sources using the
device packs you previously retrieved using the above command.

```
# Linux/Unix
./buildMchpClang.py --skip clone sources

# Windows
python3 .\buildMchpClang.py --skip clone sources
```


## About the mchpClang Projects
All of these projects with "mchpClang" in the name are here to provide you a modern Clang-based
toolchain that can be used for Microchip Technology's PIC32C and SAM lines of 32-bit microcontrollers
and microprocessors. This is meant as an alternative to the XC32 toolchain that Microchip themselves
provide that supports the latest C and C++ standards and tools (such as Clang Tidy). This toolchains
is not going to be 100% compatible with XC32 because it has things specific to the Microchip devices,
but effort was made to at least allow not-too-terrible migration from one to the other. For example,
most device register names should be the same between the two toolchains, but setting device
configuration registers is different.

Use mchpClang if you want to be able to use the latest goodies that modern C and C++ standards have
to offer on your Microchip device and you are willing to do some work and take some risk in doing so.
Use XC32 if you're looking for a seemless out-of-the-box experience that is ready to go with the
rest of Microchip's tools, such as the MPLAB X IDE and the Harmony Framework. XC32 also comes with
support from people who actually know what they're doing whereas I'm just some random dude on the
internet 😉.

You will also need to use XC32 if you need support for a device not supported here. It is unlikely
that MIPS will ever be fully supported and devices using a proprietary architecture (most of the
8-bit and 16-bit devices) will certainly never be supported. LLVM does now have an AVR backend, so
this could potentially be extended to support those devices.

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
approved by Microchip Technology, Arm Limited, or the LLVM Foundation.
