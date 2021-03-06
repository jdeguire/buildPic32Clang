# This file sets up a CMakeCache for the second stage of a simple distribution
# bootstrap build.
#
# This is based on an example cache file provided by Clang and originally came
# from "llvm/clang/cmake/caches/DistributionExample-stage2.cmake". This is modified
# to build Pic32Clang, such as by having it build support for MIPS devices and by
# adding extra tools and options not in the original file.


set(LLVM_ENABLE_PROJECTS "clang;clang-tools-extra;lld;lldb;polly;compiler-rt;libunwind;libc;libcxxabi;libcxx" CACHE STRING "")
set(LLVM_ENABLE_RUNTIMES "" CACHE STRING "")

set(LLVM_TARGETS_TO_BUILD X86;ARM;Mips CACHE STRING "")

#set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "")
set(CMAKE_BUILD_TYPE Debug CACHE STRING "")
set(CMAKE_C_FLAGS_RELWITHDEBINFO "-O3 -gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O3 -gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_C_FLAGS_DEBUG "-O1 -g" CACHE STRING "")
set(CMAKE_CXX_FLAGS_DEBUG "-O1 -g" CACHE STRING "")

# Add targets to build documentation using the Sphinx document generator. These
# will not automatically build the docs; set LLVM_BUILD_DOCS to ON for that.
set(LLVM_INCLUDE_DOCS ON CACHE BOOL "")
set(LLVM_ENABLE_SPHINX ON CACHE BOOL "")
set(SPHINX_WARNINGS_AS_ERRORS OFF CACHE BOOL "")
set(SPHINX_OUTPUT_HTML ON CACHE BOOL "")
set(SPHINX_OUTPUT_MAN ON CACHE BOOL "")

# Use libc++ and lld when building this stage 2 toolchain. These might already
# be set for bootstrap builds, but might as well be sure.
#set(LLVM_ENABLE_LLD ON CACHE BOOL "")
#set(LLVM_ENABLE_LIBCXX ON CACHE BOOL "")
#set(LLVM_BUILD_STATIC ON CACHE BOOL "")

# Stuff that supposedly helps improve build times, mostly for debug builds.
set(LLVM_OPTIMIZED_TABLEGEN ON CACHE BOOL "")
set(LLVM_USE_SPLIT_DWARF ON CACHE BOOL "")

# Clang normally defaults to looking for GNU tools like ld or libgcc instead of
# LLVM ones like lld or compiler-rt, so change that.
set(CLANG_DEFAULT_LINKER "lld" CACHE STRING "")
set(CLANG_DEFAULT_CXX_STDLIB "libc++" CACHE STRING "")
set(CLANG_DEFAULT_RTLIB "compiler-rt" CACHE STRING "")
set(CLANG_DEFAULT_UNWINDLIB "libunwind" CACHE STRING "")
set(CLANG_DEFAULT_OBJCOPY "llvm-objcopy" CACHE STRING "")

# Setup toolchain
# These are names of subdirectories under "llvm/llvm/tools".
set(LLVM_INSTALL_TOOLCHAIN_ONLY ON CACHE BOOL "")
set(LLVM_TOOLCHAIN_TOOLS
  bugpoint
  dsymutil
  llc
  llvm-ar
  llvm-config
  llvm-cxxfilt
  llvm-dwarfdump
  llvm-nm
  llvm-objdump
  llvm-ranlib
  llvm-readelf
  llvm-readobj
  llvm-size
  llvm-symbolizer
  llvm-lto
  llvm-lto2
  llvm-cov
  llvm-objcopy
  llvm-profdata
  opt
  CACHE STRING "")

set(LLVM_DISTRIBUTION_COMPONENTS
  clang
  lld
  LTO
  clang-format
  clang-resource-headers
  clang-tidy
  clangd
  builtins
#  runtimes
  ${LLVM_TOOLCHAIN_TOOLS}
  CACHE STRING "")
