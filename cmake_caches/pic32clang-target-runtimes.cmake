# This file sets up a CMakeCache for building the target-specific runtimes.
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
# -----

# This is the target triple that will be passed to Clang when building the runtimes,
# such as "mipsel-linux-gnu-musl" or "arm-none-eabi-musl".
set(PIC32CLANG_TARGET_TRIPLE "" CACHE STRING "The target triple for which to build the runtimes")

# This is a semicolon-delimited list of extra flags to use when building the runtime 
# libraries. These should include target-specific flags like "-march" and FPU flags as
# well as optimization flags. Do not include the "-target" option because this is already
# handled with the PIC32CLANG_TARGET_TRIPLE option. Flags and their arguments should be 
# passed as separate entries (ie. have a semicolon between them) if there would normally
# be a space between them. Put double quotes around entries that may have spaces in them,
# like paths, to have them treated like a single entry.
set(PIC32CLANG_RUNTIME_FLAGS "" CACHE STRING "Compiler flags for building the runtimes")

# The path to the Musl C library headers. Musl needs to have been built first before the
# runtimes can be built because some headers are generated as part of the build.
# The Python script in the parent directory will do this for you.
set(PIC32CLANG_MUSL_INCLUDES "" CACHE PATH "Path to Musl C library headers")

# The path of the sysroot of Clang, presumably one that was just built for Pic32Clang,
# that will build the runtimes. If you are doing a two-stage build (which is what the Python
# script in the parent directory does) then you will want to point this to the stage2 build
# location instead of the installed location. This is because the build location has extra
# CMake files that are needed by the runtime build. Find it at 
# "<build-prefix>/llvm/tools/clang/stage2-bins".
set(PIC32CLANG_SYSROOT "" CACHE PATH "The root of the compiler that will build the runtimes")

# -----
# Set up options supplied above.
# -----

if(PIC32CLANG_TARGET_TRIPLE STREQUAL "")
    message(FATAL_ERROR "PIC32CLANG_TARGET_TRIPLE is empty. Provide a valid target.")
endif()

if(PIC32CLANG_MUSL_INCLUDES STREQUAL "")
    message(FATAL_ERROR "PIC32CLANG_MUSL_INCLUDES is empty. Provide a valid path.")
endif()

if(PIC32CLANG_SYSROOT STREQUAL "")
    message(FATAL_ERROR "PIC32CLANG_SYSROOT is empty. Provide a valid sysroot.")
endif()

if(NOT IS_DIRECTORY ${PIC32CLANG_MUSL_INCLUDES})
    message(FATAL_ERROR "PIC32CLANG_MUSL_INCLUDES (${PIC32CLANG_MUSL_INCLUDES}) is not a directory.")
endif()

if(NOT IS_DIRECTORY ${PIC32CLANG_SYSROOT})
    message(FATAL_ERROR "PIC32CLANG_SYSROOT (${PIC32CLANG_SYSROOT}) is not a directory.")
endif()

# Add options that will apply regardless of target.
list(APPEND PIC32CLANG_RUNTIME_FLAGS
    -isystem
    ${PIC32CLANG_MUSL_INCLUDES}
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
    -D_LIBCPP_HAS_TIMESPEC_GET
    -D_LIBCPP_HAS_C11_FEATURES)

list(JOIN PIC32CLANG_RUNTIME_FLAGS " " PIC32CLANG_RUNTIME_FLAGS)

# -----
# End Pic32Clang-specific stuff.
# -----

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${PIC32CLANG_RUNTIME_FLAGS}" CACHE STRING "")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${PIC32CLANG_RUNTIME_FLAGS}" CACHE STRING "")
set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} ${PIC32CLANG_RUNTIME_FLAGS}" CACHE STRING "")

set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "")
set(CMAKE_C_FLAGS_RELWITHDEBINFO "-gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_ASM_FLAGS_RELWITHDEBINFO "-gline-tables-only -DNDEBUG" CACHE STRING "")

set(CMAKE_CROSSCOMPILING ON CACHE BOOL "")
set(CMAKE_SYSROOT "${PIC32CLANG_SYSROOT}" CACHE PATH "")
set(CMAKE_C_COMPILER "${PIC32CLANG_SYSROOT}/bin/clang" CACHE PATH "")
set(CMAKE_CXX_COMPILER "${PIC32CLANG_SYSROOT}/bin/clang++" CACHE PATH "")
set(CMAKE_AR "${PIC32CLANG_SYSROOT}/bin/llvm-ar" CACHE PATH "")
set(CMAKE_NM "${PIC32CLANG_SYSROOT}/bin/llvm-nm" CACHE PATH "")
set(CMAKE_RANLIB "${PIC32CLANG_SYSROOT}/bin/llvm-ranlib" CACHE PATH "")
set(CMAKE_C_COMPILER_TARGET ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
set(CMAKE_CXX_COMPILER_TARGET ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
set(CMAKE_ASM_COMPILER_TARGET ${PIC32CLANG_TARGET_TRIPLE} CACHE STRING "")
# This needs to be "Linux" because otherwise a CMake check will fail claiming
# it cannot determine the target platform. 
set(CMAKE_SYSTEM_NAME Linux CACHE STRING "")
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY CACHE STRING "")

set(LLVM_INCLUDE_DOCS ON CACHE BOOL "")
set(LLVM_ENABLE_SPHINX ON CACHE BOOL "")
set(LLVM_COMPILER_CHECKED ON CACHE BOOL "")
set(LLVM_ENABLE_RUNTIMES all CACHE STRING "")

set(COMPILER_RT_OS_DIR baremetal CACHE STRING "")
set(COMPILER_RT_BAREMETAL_BUILD ON CACHE BOOL "")
set(COMPILER_RT_DEFAULT_TARGET_ONLY ON CACHE BOOL "")
set(COMPILER_RT_STANDALONE_BUILD ON CACHE BOOL "")
# We cannot build most of these now because they need the builtins to have been already built.
set(COMPILER_RT_BUILD_BUILTINS ON CACHE BOOL "")
set(COMPILER_RT_BUILD_CRT ON CACHE BOOL "")
set(COMPILER_RT_BUILD_SANITIZERS OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_XRAY OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_LIBFUZZER OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_PROFILE OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_MEMPROF OFF CACHE BOOL "")
set(COMPILER_RT_USE_BUILTINS_LIBRARY ON CACHE BOOL "")
set(COMPILER_RT_EXCLUDE_ATOMIC_BUILTIN OFF CACHE BOOL "")

set(LIBUNWIND_ENABLE_STATIC ON CACHE BOOL "")
set(LIBUNWIND_ENABLE_SHARED OFF CACHE BOOL "")
set(LIBUNWIND_USE_COMPILER_RT ON CACHE BOOL "")
set(LIBUNWIND_ENABLE_CROSS_UNWINDING OFF CACHE BOOL "")

set(LIBCXX_HAS_MUSL_LIBC ON CACHE BOOL "")
set(LIBCXX_STANDALONE_BUILD ON CACHE BOOL "")
set(LIBCXX_ENABLE_STATIC ON CACHE BOOL "")
set(LIBCXX_ENABLE_SHARED OFF CACHE BOOL "")
set(LIBCXX_ENABLE_FILESYSTEM ON CACHE BOOL "")
set(LIBCXX_ENABLE_EXPERIMENTAL_LIBRARY ON CACHE BOOL "")
set(LIBCXX_CXX_ABI libcxxabi CACHE STRING "")
set(LIBCXX_USE_COMPILER_RT ON CACHE BOOL "")
set(LIBCXX_USE_LLVM_UNWINDER ON CACHE BOOL "")
set(LIBCXX_HAS_PTHREAD_API ON CACHE BOOL "")

set(LIBCXXABI_BAREMETAL ON CACHE BOOL "")
set(LIBCXXABI_STANDALONE_BUILD ON CACHE BOOL "")
set(LIBCXXABI_ENABLE_STATIC ON CACHE BOOL "")
set(LIBCXXABI_ENABLE_SHARED OFF CACHE BOOL "")
set(LIBCXXABI_USE_LLVM_UNWINDER ON CACHE BOOL "")
set(LIBCXXABI_USE_COMPILER_RT ON CACHE BOOL "")
set(LIBCXXABI_HAS_PTHREAD_API ON CACHE BOOL "")
set(LIBCXXABI_LIBCXX_INCLUDES "${CMAKE_INSTALL_PREFIX}/include/c++/v1" CACHE PATH "")

# This prints out variables and was found on Stack Overflow.
#get_cmake_property(_variableNames VARIABLES)
#list (SORT _variableNames)
#foreach (_variableName ${_variableNames})
#    message(STATUS "${_variableName}=${${_variableName}}")
#endforeach()