# This file sets up a CMakeCache for building the target-specific runtimes, such
# as the C++ libraries, unwinder, and any sanitizers. The target-specific built-in
# functions need to have already been built because these runtimes depend on them.
#
# This started off based on an example cache file provided by Clang located
# at "llvm/clang/cmake/caches/BaremetalARM.cmake". This has been modified
# a lot to just build the runtimes for MIPS and ARM devices.
#
# The original example file did not have a copyright or license notice, but
# Clang is covered under a modified Apache 2.0 license. Presumably, that
# includes the example code and so this will follow suit. A copy of the
# license is provided in LICENSE.txt.

# -----
# Pic32Clang-specific options; define these on the command line when using this script.
# 

# This is the target triple that will be passed to Clang when building the runtimes,
# such as "mipsel-linux-gnu" or "arm-none-eabi".
set(PIC32CLANG_TARGET_TRIPLE "" CACHE STRING "The target triple for which to build the runtimes")

# This is a semicolon-delimited list of extra flags to use when building the runtime 
# libraries. These should include target-specific flags like "-march" and FPU flags as
# well as optimization flags. Do not include the "-target" option because this is already
# handled with the PIC32CLANG_TARGET_TRIPLE option. Flags and their arguments should be 
# passed as separate entries (ie. have a semicolon between them) if there would normally
# be a space between them. Put double quotes around entries that may have spaces in them,
# like paths, to have them treated like a single entry.
set(PIC32CLANG_RUNTIME_FLAGS "" CACHE STRING "Compiler flags for building the runtimes")

# The directory path to the toolchain, presumably one that was just built for Pic32Clang,
# that will build the runtimes. If you are doing a two-stage build (which is what the Python
# script in the parent directory does) then you will want to point this to the stage2 build
# location instead of the installed location. This is because the build location has extra
# CMake files that are needed by the runtime build. Find it at 
# "<build-prefix>/llvm/tools/clang/stage2-bins".
set(PIC32CLANG_PATH "" CACHE PATH "The directory path to the compiler that will build the runtimes")

# Use this to add a suffix to the location at which the libraries will be installed. This is used by
# the Python script in the parent directory to create subdirectories for different variants of the
# libraries. For example, it would set this to "r2/micromips" to install Mips32r2 microMIPS libraries 
# at "<prefix>/lib/r2/micromips".
set(PIC32CLANG_LIBDIR_SUFFIX "" CACHE STRING "Optionally add a suffix to the library directory name")


# Set up options supplied above.
if(PIC32CLANG_TARGET_TRIPLE STREQUAL "")
    message(FATAL_ERROR "PIC32CLANG_TARGET_TRIPLE is empty. Provide a valid target.")
endif()

if(PIC32CLANG_PATH STREQUAL "")
    message(FATAL_ERROR "PIC32CLANG_PATH is empty. Provide a valid sysroot.")
endif()

if(NOT IS_DIRECTORY ${PIC32CLANG_PATH})
    message(FATAL_ERROR "PIC32CLANG_PATH (${PIC32CLANG_PATH}) is not a directory.")
endif()

# Add options that will apply regardless of target.
# TODO: We probably need to revisit these, especially if we are not using Musl anymore.
list(APPEND PIC32CLANG_RUNTIME_FLAGS
    -isystem
    ${CMAKE_INSTALL_PREFIX}/include
    -static
    # Undefine these so that the output is the same regardless of build platform.
    # Otherwise, libc++ will use platform-specific code based on which is defined.
    -U__linux__
    -U__APPLE__
    -U_WIN32
    # These are defined if libc++ is configured to use Musl and __linux__ is defined.
    # Define them manually so that they work the same regardless of build platform.
    -D_LIBCPP_HAS_ALIGNED_ALLOC
    -D_LIBCPP_HAS_QUICK_EXIT
    # This is already defined by libc++ since we are using LLVM-libc.
    #-D_LIBCPP_HAS_TIMESPEC_GET
    -D_LIBCPP_HAS_C11_FEATURES
    -D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE
    # The Libc build turns warning into errors and this prevents such an error from
    # showing up an v6m targets. They do not support the ARM atomic instructions.
    -Wno-atomic-alignment
    # There is currently no CMake option for this, but this define appears to remove
    # the usage of tables in libc's printf() float conversions if they are not needed.
    -DLIBC_COPT_FLOAT_TO_STR_NO_TABLE
)

list(JOIN PIC32CLANG_RUNTIME_FLAGS " " PIC32CLANG_RUNTIME_FLAGS)

#
# End Pic32Clang-specific stuff.
# -----

# -----
# CMake general stuff
#
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${PIC32CLANG_RUNTIME_FLAGS}" CACHE STRING "")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${PIC32CLANG_RUNTIME_FLAGS}" CACHE STRING "")
set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} ${PIC32CLANG_RUNTIME_FLAGS}" CACHE STRING "")

# Set optimization and debug options based on the value of CMAKE_BUILD_TYPE. Possible values for
# that are "Release", "Debug", "RelWithDebInfo", and "MinSizeRel". Set the build type on the
# command line when using this cmake cache. We use O2 optimizations here because it should be a
# good balance of size and speed for embedded libraries. CMake will by default use O3 for release
# builds, but that can make the resulting binary larger than O2.
set(CMAKE_C_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "")
set(CMAKE_ASM_FLAGS_RELEASE "-O2 -DNDEBUG" CACHE STRING "")

set(CMAKE_C_FLAGS_DEBUG "-g" CACHE STRING "")
set(CMAKE_CXX_FLAGS_DEBUG "-g" CACHE STRING "")
set(CMAKE_ASM_FLAGS_DEBUG "-g" CACHE STRING "")

set(CMAKE_C_FLAGS_RELWITHDEBINFO "-O2 -gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O2 -gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_ASM_FLAGS_RELWITHDEBINFO "-O2 -gline-tables-only -DNDEBUG" CACHE STRING "")

set(CMAKE_C_FLAGS_MINSIZEREL "-Oz -DNDEBUG" CACHE STRING "")
set(CMAKE_CXX_FLAGS_MINSIZEREL "-Oz -DNDEBUG" CACHE STRING "")
set(CMAKE_ASM_FLAGS_MINSIZEREL "-Oz -DNDEBUG" CACHE STRING "")


set(CMAKE_CROSSCOMPILING ON CACHE BOOL "")
set(CMAKE_SYSROOT "${PIC32CLANG_PATH}" CACHE PATH "")
set(CMAKE_C_COMPILER "${PIC32CLANG_PATH}/bin/clang${CMAKE_HOST_EXECUTABLE_SUFFIX}" CACHE PATH "")
set(CMAKE_CXX_COMPILER "${PIC32CLANG_PATH}/bin/clang++${CMAKE_HOST_EXECUTABLE_SUFFIX}" CACHE PATH "")
set(CMAKE_AR "${PIC32CLANG_PATH}/bin/llvm-ar${CMAKE_HOST_EXECUTABLE_SUFFIX}" CACHE PATH "")
set(CMAKE_NM "${PIC32CLANG_PATH}/bin/llvm-nm${CMAKE_HOST_EXECUTABLE_SUFFIX}" CACHE PATH "")
set(CMAKE_RANLIB "${PIC32CLANG_PATH}/bin/llvm-ranlib${CMAKE_HOST_EXECUTABLE_SUFFIX}" CACHE PATH "")
set(CMAKE_C_COMPILER_TARGET ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
set(CMAKE_CXX_COMPILER_TARGET ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
set(CMAKE_ASM_COMPILER_TARGET ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
# This needs to be "Linux" because otherwise a CMake check will fail claiming
# it cannot determine the target platform. 
# TODO: Should this be "Generic" instead? That's what the example CMake cache
#       at /llvm/clang/cmake/caches/BaremetalARM.cmake does. That is what the
#       MPLAB Extensions for VS Code use, too. Does LLVM barf on "Generic"?
set(CMAKE_SYSTEM_NAME Linux CACHE STRING "")
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY CACHE STRING "")
# TODO: Should we enable CMAKE_EXPORT_COMPILE_COMMANDS? Do we need this for the runtimes?

# -----
# LLVM stuff
#
# Add targets to build documentation using the Sphinx document generator if LLVM_BUILD_DOCS is ON.
if(LLVM_BUILD_DOCS)
  set(LLVM_INCLUDE_DOCS ON CACHE BOOL "")
  set(LLVM_ENABLE_SPHINX ON CACHE BOOL "")
  set(SPHINX_WARNINGS_AS_ERRORS OFF CACHE BOOL "")
  set(SPHINX_OUTPUT_HTML ON CACHE BOOL "")
  set(SPHINX_OUTPUT_MAN ON CACHE BOOL "")
else()
  set(LLVM_INCLUDE_DOCS OFF CACHE BOOL "")
  set(LLVM_ENABLE_SPHINX OFF CACHE BOOL "")
endif()

set(LLVM_COMPILER_CHECKED ON CACHE BOOL "")
set(LLVM_ENABLE_PER_TARGET_RUNTIME_DIR OFF CACHE BOOL "")
set(LLVM_ENABLE_RUNTIMES "compiler-rt;libc;libcxx;libcxxabi;libunwind" CACHE STRING "")
set(LLVM_LIBDIR_SUFFIX "/${PIC32CLANG_LIBDIR_SUFFIX}" CACHE STRING "")
set(RUNTIMES_USE_LIBC "llvm-libc" CACHE STRING "")

# -----
# Compiler-RT
#
set(COMPILER_RT_OS_DIR "${PIC32CLANG_LIBDIR_SUFFIX}/" CACHE STRING "")
set(COMPILER_RT_BAREMETAL_BUILD ON CACHE BOOL "")
set(COMPILER_RT_DEFAULT_TARGET_ONLY ON CACHE BOOL "")
set(COMPILER_RT_BUILD_BUILTINS ON CACHE BOOL "")
set(COMPILER_RT_BUILD_CRT ON CACHE BOOL "")
# These will not build because platform macros have been undefined above. Defining "__linux__"
# still fails because the build then looks for linux-specific headers I don't yet have.
#set(COMPILER_RT_BUILD_SANITIZERS ON CACHE BOOL "")
#set(COMPILER_RT_BUILD_XRAY ON CACHE BOOL "")
#set(COMPILER_RT_BUILD_LIBFUZZER ON CACHE BOOL "")
#set(COMPILER_RT_BUILD_PROFILE ON CACHE BOOL "")
#set(COMPILER_RT_BUILD_MEMPROF ON CACHE BOOL "")
set(COMPILER_RT_BUILD_SANITIZERS OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_XRAY OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_LIBFUZZER OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_PROFILE OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_MEMPROF OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_CTX_PROFILE OFF CACHE BOOL "")
# Comment this out for now because it causes an error about not being able to find
# the builtins library for the target architecture. 
#set(COMPILER_RT_USE_BUILTINS_LIBRARY ON CACHE BOOL "")
# Exclude this because it fails to build on Armv6-m. That arch does not support the instructions
# to allow atomic access. In the future it might be possible to enable this for all but Armv6-m.
set(COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN ON CACHE BOOL "")
set(COMPILER_RT_BUILD_SCUDO_STANDALONE_WITH_LLVM_LIBC OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_GWP_ASAN OFF CACHE BOOL "")
set(COMPILER_RT_SCUDO_STANDALONE_BUILD_SHARED OFF CACHE BOOL "")

# -----
# Libunwind
#
set(LIBUNWIND_ENABLE_STATIC ON CACHE BOOL "")
set(LIBUNWIND_ENABLE_SHARED OFF CACHE BOOL "")
set(LIBUNWIND_ENABLE_THREADS OFF CACHE BOOL "")
set(LIBUNWIND_USE_COMPILER_RT ON CACHE BOOL "")
set(LIBUNWIND_ENABLE_CROSS_UNWINDING OFF CACHE BOOL "")
set(LIBUNWIND_IS_BAREMETAL ON CACHE BOOL "")
set(LIBUNWIND_ENABLE_ASSERTIONS OFF CACHE BOOL "")

# -----
# LLVM-libc
#
# TODO: Do we want to include Scudo? It's a more secure memory allocator. If so, there are a few
#       Compiler-RT options above related to Scudo. This might not be supported on baremetal.
set(LLVM_LIBC_FULL_BUILD ON CACHE BOOL "")
set(LLVM_LIBC_INCLUDE_SCUDO OFF CACHE BOOL "")
set(LIBC_TARGET_TRIPLE ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
# This puts all C declarations into the header files even if the implementation is not provided on
# our target. Do this so we can provide our own implementations for things like file IO or time
# functions.
set(LLVM_LIBC_ALL_HEADERS ON CACHE BOOL "")

# Printf options:
# Some of these are disabled by default for baremetal targets. Explicity put the options here
# so we can tune them how we want.
# See "llvm/libc/config/baremetal/config.json" for the defaults. 
# See "llvm/libc/src/__support/float_to_string.h" and "llvm/libc/docs/dev/printf_behavior.rst"
# for additional explanations for these. 
set(LIBC_CONF_PRINTF_DISABLE_INDEX_MODE ON CACHE STRING "")
set(LIBC_CONF_PRINTF_DISABLE_STRERROR ON CACHE STRING "")
set(LIBC_CONF_PRINTF_DISABLE_WRITE_INT ON CACHE STRING "")
set(LIBC_CONF_PRINTF_DISABLE_FIXED_POINT OFF CACHE STRING "")
set(LIBC_CONF_PRINTF_DISABLE_FLOAT OFF CACHE STRING "")
set(LIBC_CONF_PRINTF_FLOAT_TO_STR_NO_SPECIALIZE_LD ON CACHE STRING "")
set(LIBC_CONF_PRINTF_FLOAT_TO_STR_USE_DYADIC_FLOAT ON CACHE STRING "")
# Enabling this FLOAT320 option will reduce binary size by 9kB but make floating point conversions
# take about twice as long (~350us vs ~180us in a very basic example). This assumes that
# LIBC_COPT_FLOAT_TO_STR_NO_TABLE is defined in the runtime flags above.
set(LIBC_CONF_PRINTF_FLOAT_TO_STR_USE_FLOAT320 OFF CACHE STRING "")
set(LIBC_CONF_PRINTF_FLOAT_TO_STR_USE_MEGA_LONG_DOUBLE_TABLE OFF CACHE STRING "")

set(LIBC_CONF_SCANF_DISABLE_FLOAT OFF CACHE STRING "")
set(LIBC_CONF_SCANF_DISABLE_INDEX_MODE ON CACHE STRING "")

# -----
# Libc++
#
set(LIBCXX_ENABLE_STATIC ON CACHE BOOL "")
set(LIBCXX_ENABLE_SHARED OFF CACHE BOOL "")
set(LIBCXX_ENABLE_EXPERIMENTAL_LIBRARY ON CACHE BOOL "")
set(LIBCXX_CXX_ABI libcxxabi CACHE STRING "")
set(LIBCXX_ENABLE_STATIC_ABI_LIBRARY ON CACHE BOOL "")
set(LIBCXX_USE_COMPILER_RT ON CACHE BOOL "")
set(LIBCXX_ENABLE_TIME_ZONE_DATABASE OFF CACHE BOOL "")
set(LIBCXX_INCLUDE_BENCHMARKS OFF CACHE BOOL "")

set(LIBCXX_ENABLE_EXCEPTIONS ON CACHE BOOL "")
set(LIBCXX_HARDENING_MODE fast CACHE STRING "")

# TODO: Libc++ might be including its own giant tables for its own std::print stuff. Are there
#       options to reduce those like with Libc? It's basically including duplicates.
# TODO: Do I need to disable Unicode with LIBCXX_ENABLE_UNICODE set to OFF? The tables are big,
#       but are they *that* big?

# TODO: Disable filesystem for now and revisit this in the future. It would be nice to
#       have a standard filesystem interface, even if we have to implement the underlying
#       layer ourselves.
# set(LIBCXX_ENABLE_FILESYSTEM ON CACHE BOOL "")
set(LIBCXX_ENABLE_FILESYSTEM OFF CACHE BOOL "")
set(LIBCXX_USE_LLVM_UNWINDER ON CACHE BOOL "")
# Disable these for now because of an undefined symbol error for TIME_MONOTONIC
# Threads must be disabled to disable the monotonic clock.
# set(LIBCXX_HAS_PTHREAD_API ON CACHE BOOL "")
set(LIBCXX_ENABLE_MONOTONIC_CLOCK OFF CACHE BOOL "")
set(LIBCXX_ENABLE_THREADS OFF CACHE BOOL "")
set(LIBCXX_HAS_PTHREAD_API OFF CACHE BOOL "")
# We need to disable wide character support because LLVM-libc has very few wchar functions
# implemented at this time. We can revisit this in the future.
set(LIBCXX_ENABLE_WIDE_CHARACTERS OFF CACHE BOOL "")
# LLVM-libc recently included locale stuff in the baremetal build, but libc++ expects to be able to
# use C file IO functions, which we do not yet have on baremetal libc. This ends up disabling a lot
# of the stream interface, but we avoid those on embedded anyway.
set(LIBCXX_ENABLE_LOCALIZATION OFF CACHE BOOL "")
# TODO: Turn this off for now but revisit it in the future. I'm not sure what it does.
#       Really, anything in embedded would be a terminal, but maybe we want this off if
#       libc++ will use this to try printing ANSI escape codes or something.
set(LIBCXX_HAS_TERMINAL_AVAILABLE OFF CACHE BOOL "")
# TODO: Maybe revisit this if we can create a way to access random number generators on
#       some of our devices.
set(LIBCXX_ENABLE_RANDOM_DEVICE OFF CACHE BOOL "")

# -----
# Libc++abi
#
set(LIBCXXABI_BAREMETAL ON CACHE BOOL "")
set(LIBCXXABI_ENABLE_STATIC ON CACHE BOOL "")
set(LIBCXXABI_ENABLE_SHARED OFF CACHE BOOL "")
set(LIBCXXABI_USE_LLVM_UNWINDER ON CACHE BOOL "")
set(LIBCXXABI_USE_COMPILER_RT ON CACHE BOOL "")
# set(LIBCXXABI_HAS_PTHREAD_API ON CACHE BOOL "")
# Disable these for now to match libcxx a few lines above.
set(LIBCXXABI_HAS_PTHREAD_API OFF CACHE BOOL "")
set(LIBCXXABI_ENABLE_THREADS OFF CACHE BOOL "")
set(LIBCXXABI_ENABLE_ASSERTIONS OFF CACHE BOOL "")
set(LIBCXXABI_ENABLE_EXCEPTIONS ON CACHE BOOL "")

# This prints out variables and was found on Stack Overflow.
#get_cmake_property(_variableNames VARIABLES)
#list (SORT _variableNames)
#foreach (_variableName ${_variableNames})
#    message(STATUS "${_variableName}=${${_variableName}}")
#endforeach()
