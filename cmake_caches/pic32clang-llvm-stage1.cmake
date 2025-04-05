# This file sets up a CMakeCache for a simple distribution bootstrap build.
#
# This is based on an example cache file provided by Clang and originally came
# from "llvm/clang/cmake/caches/DistributionExample.cmake".
#
# The original example file did not have a copyright or license notice, but
# Clang is covered under a modified Apache 2.0 license. Presumably, that
# includes the example code and so this will follow suit. A copy of the
# license is provided in LICENSE.txt.

# Enable LLVM projects and runtimes
# The proper variable to check is 'MSVC', but that is not yet checked when this file is parsed.
# The best we can do is 'WIN32' for now. This check is here because libunwind and libcxxabi
# are not supported with MSVC.
set(LLVM_ENABLE_PROJECTS "clang;clang-tools-extra;lld;polly" CACHE STRING "")
if(WIN32)
  set(LLVM_ENABLE_RUNTIMES "compiler-rt;libcxx" CACHE STRING "")
else()
  set(LLVM_ENABLE_RUNTIMES "compiler-rt;libunwind;libcxx;libcxxabi" CACHE STRING "")
endif()

# Only build the native target in stage1 since it is a throwaway build.
set(LLVM_TARGETS_TO_BUILD Native CACHE STRING "")

# Optimize the stage1 compiler, but don't LTO it because that wastes time.
set(CMAKE_BUILD_TYPE Release CACHE STRING "")

# Setting up the stage2 LTO option needs to be done on the stage1 build so that
# the proper LTO library dependencies can be connected.
set(BOOTSTRAP_LLVM_ENABLE_LTO ON CACHE BOOL "")

if (NOT APPLE)
  # Since LLVM_ENABLE_LTO is ON we need a LTO capable linker
  set(BOOTSTRAP_LLVM_ENABLE_LLD ON CACHE BOOL "")
endif()

# Build minimum Compiler-RT for stage1
set(COMPILER_RT_DEFAULT_TARGET_ONLY ON CACHE BOOL "")
set(COMPILER_RT_BUILD_SANITIZERS OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_XRAY OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_LIBFUZZER OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_PROFILE OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_MEMPROF OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_CTX_PROFILE OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_ORC OFF CACHE BOOL "")

# Expose stage2 targets through the stage1 build configuration.
set(CLANG_BOOTSTRAP_TARGETS
  check-all
  check-llvm
  check-clang
  llvm-config
  test-suite
  test-depends
  llvm-test-depends
  clang-test-depends
  distribution
  install-distribution
  clang CACHE STRING "")

# Setup the bootstrap build.
set(CLANG_ENABLE_BOOTSTRAP ON CACHE BOOL "")

if(STAGE2_CACHE_FILE)
  set(CLANG_BOOTSTRAP_CMAKE_ARGS
    -C ${STAGE2_CACHE_FILE}
    CACHE STRING "")
else()
  set(CLANG_BOOTSTRAP_CMAKE_ARGS
    -C ${CMAKE_CURRENT_LIST_DIR}/pic32clang-llvm-stage2.cmake
    CACHE STRING "")
endif()
