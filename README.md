# buildPic32Clang
A Python script to build Clang for PIC32 and SAM devices along with any supporting libraries.

This README will get more detailed in the future (I hope...) as I complete more of the script.  At this point, it doesn't actually do much.

# Requirements
This script was written using Python 3.8 and does not require any external dependencies.  In addition, your platform needs to be able to build and run Clang (duh) and needs to support ANSI terminal control codes to make the output readable.  This means Macs, Unixes, and Windows 10.

So far, this script has been run only under the Windows Subsytem for Linux (WSL) on Windows 10. The intent is for it to also support running on a Windows terminal as well, but that has not yet been tested very much.

# How to Run
For now, this script can be run by opening up a terminal interface and running ```./buildPic32Clang.py``` (Unix/Linux/WSL/etc.) or ```python3 .\buildPic32Clang.py``` (Windows).  I plan to add command-line arguments in the future to control things like skipping certain parts of the build or just getting the sources without building--stuff like that.

# About the pic32Clang Projects
All of these projects with "pic32Clang" in the name are here to provide you a modern Clang-based toolchain that can be used for Microchip Technology's PIC32 and SAM lines of 32-bit microcontrollers and microprocessors (not yet, but one day).  This is meant as an alternative to the XC32 toolchain that Microchip themselves provide that supports the latest C and C++ standards and tools (such as Clang Tidy).  This toolchains is not going to be 100% compatible with XC32 because it has things specific to the Microchip devices, but effort was made to at least allow not-too-terrible migration from one to the other.  For example, most device register names should be the same between the two toolchains, but setting device configuration registers is different.

Use pic32Clang if you want to be able to use the latest goodies that modern C and C++ standards have to offer on your Microchip device and you are willing to do some work and take some risk in doing so.  Use XC32 if you're looking for a seemless out-of-the-box experience that is ready to go with the rest of Microchip's tools, such as the MPLAB X IDE and the Harmony Framework.  XC32 also comes with support from people who actually know what they're doing whereas I'm just some random dude on the internet 😉.

For the closest-to-native experience with Microchip tools, you will also want to use the ```toolchainPic32Clang``` plugin for MPLAB X.  That plugin allows you to use the familiar MPLAB X IDE to set options and will pass the correct options to Clang to get it to build for your device.  You can even have it run Clang Tidy instead of invoking the compiler to check your project (it's a little kludgy right now, but it does run!).  Even if you do not intend to use MPLAB X for normal development, you'll want to at least give it a go to see how Clang is invoked.

# License
See the LICENSE file for the full thing, but basically this is licensed using the BSD 3-clause license because I don't know anything about licenses and that one seemed good.

The CMake cache files located under "cmake_caches" are licensed under the modified Apache 2.0 license used by Clang. Those files started out as copies of exmaple CMake files from the Clang source and so presumably they must comply with Clang's license. Again, I know nothing about licenses, so this also seems good. 
