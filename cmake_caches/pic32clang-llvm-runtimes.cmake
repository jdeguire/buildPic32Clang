# These were taken from the pic32clang-llvm-stageN files. The example Clang files
# upon which those are based were updated when LLVM moved to a Git monorepo, but
# the file upon which this is based was not updated, so we need these entries here.
set(LLVM_ENABLE_PROJECTS "clang;clang-tools-extra;lld" CACHE STRING "")
set(LLVM_ENABLE_RUNTIMES "compiler-rt;libcxx;libcxxabi" CACHE STRING "")
set(CMAKE_BUILD_TYPE Release CACHE STRING "")

set(LLVM_TARGETS_TO_BUILD ARM;X86 CACHE STRING "")


# Pic32Clang-specific stuff; define these on the command line when using this script.
#

# This is a semicolon-delimited list of extra flags to use when building the runtime 
# libraries. Flags and their arguments should be passed as separate entries (ie. have
# a semicolon between them) if there would normally be a space between them. Put double
# quotes around entries that may have spaces in them, like paths, to have them treated
# like a single entry.
set(PIC32CLANG_EXTRA_FLAGS "" CACHE STRING "Flags to pass to compiler when building runtime libs")

# Join the above list into a string. I could have just passed in a string instead of a list and
# removed this step, but doing it this way makes it easier to add entries that are quoted, such
# as paths.
list(JOIN PIC32CLANG_EXTRA_FLAGS " " _PIC32_RUNTIME_FLAGS)

#
# End Pic32Clang-specific stuff.


# Builtins
set(LLVM_BUILTIN_TARGETS "armv7m-none-eabi;armv6m-none-eabi;armv7em-none-eabi" CACHE STRING "Builtin Targets")

set(BUILTINS_armv6m-none-eabi_CMAKE_SYSROOT ${BAREMETAL_ARMV6M_SYSROOT} CACHE STRING "armv6m-none-eabi Sysroot")
set(BUILTINS_armv6m-none-eabi_CMAKE_SYSTEM_NAME Generic CACHE STRING "armv6m-none-eabi System Name")
set(BUILTINS_armv6m-none-eabi_COMPILER_RT_BAREMETAL_BUILD ON CACHE BOOL "armv6m-none-eabi Baremetal build")
set(BUILTINS_armv6m-none-eabi_CMAKE_C_FLAGS "${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv6m-none-eabi C Flags")
set(BUILTINS_armv6m-none-eabi_CMAKE_CXX_FLAGS "${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv6m-none-eabi C++ Flags")
set(BUILTINS_armv6m-none-eabi_CMAKE_ASM_FLAGS "${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv6m-none-eabi ASM Flags")
set(BUILTINS_armv6m-none-eabi_COMPILER_RT_OS_DIR "baremetal" CACHE STRING "armv6m-none-eabi os dir")

set(BUILTINS_armv7m-none-eabi_CMAKE_SYSROOT ${BAREMETAL_ARMV7M_SYSROOT} CACHE STRING "armv7m-none-eabi Sysroot")
set(BUILTINS_armv7m-none-eabi_CMAKE_SYSTEM_NAME Generic CACHE STRING "armv7m-none-eabi System Name")
set(BUILTINS_armv7m-none-eabi_COMPILER_RT_BAREMETAL_BUILD ON CACHE BOOL "armv7m-none-eabi Baremetal build")
set(BUILTINS_armv7m-none-eabi_CMAKE_C_FLAGS "-mfpu=fp-armv8 ${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv7m-none-eabi C Flags")
set(BUILTINS_armv7m-none-eabi_CMAKE_CXX_FLAGS "-mfpu=fp-armv8 ${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv7m-none-eabi C++ Flags")
set(BUILTINS_armv7m-none-eabi_CMAKE_ASM_FLAGS "-mfpu=fp-armv8 ${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv7m-none-eabi ASM Flags")
set(BUILTINS_armv7m-none-eabi_COMPILER_RT_OS_DIR "baremetal" CACHE STRING "armv7m-none-eabi os dir")

set(BUILTINS_armv7em-none-eabi_CMAKE_SYSROOT ${BAREMETAL_ARMV7EM_SYSROOT} CACHE STRING "armv7em-none-eabi Sysroot")
set(BUILTINS_armv7em-none-eabi_CMAKE_SYSTEM_NAME Generic CACHE STRING "armv7em-none-eabi System Name")
set(BUILTINS_armv7em-none-eabi_COMPILER_RT_BAREMETAL_BUILD ON CACHE BOOL "armv7em-none-eabi Baremetal build")
set(BUILTINS_armv7em-none-eabi_CMAKE_C_FLAGS "-mfpu=fp-armv8 ${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv7em-none-eabi C Flags")
set(BUILTINS_armv7em-none-eabi_CMAKE_CXX_FLAGS "-mfpu=fp-armv8 ${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv7em-none-eabi C++ Flags")
set(BUILTINS_armv7em-none-eabi_CMAKE_ASM_FLAGS "-mfpu=fp-armv8 ${_PIC32_RUNTIME_FLAGS}" CACHE STRING "armv7em-none-eabi ASM Flags")
set(BUILTINS_armv7em-none-eabi_COMPILER_RT_OS_DIR "baremetal" CACHE STRING "armv7em-none-eabi os dir")

set(LLVM_INSTALL_TOOLCHAIN_ONLY ON CACHE BOOL "")
set(LLVM_TOOLCHAIN_TOOLS
  dsymutil
  llc
  llvm-ar
  llvm-cxxfilt
  llvm-dwarfdump
  llvm-nm
  llvm-objdump
  llvm-ranlib
  llvm-readobj
  llvm-size
  llvm-symbolizer
  opt
  CACHE STRING "")

set(LLVM_DISTRIBUTION_COMPONENTS
  clang
  lld
  clang-resource-headers
  builtins-armv6m-none-eabi
  builtins-armv7m-none-eabi
  builtins-armv7em-none-eabi
  runtimes
  ${LLVM_TOOLCHAIN_TOOLS}
  CACHE STRING "")

# This prints out variables and was found on Stack Overflow.
#get_cmake_property(_variableNames VARIABLES)
#list (SORT _variableNames)
#foreach (_variableName ${_variableNames})
#    message(STATUS "${_variableName}=${${_variableName}}")
#endforeach()