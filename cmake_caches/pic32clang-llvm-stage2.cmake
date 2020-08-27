# This file sets up a CMakeCache for the second stage of a simple distribution
# bootstrap build.
#
# This is based on an example cache file provided by Clang and originally came
# from "llvm/clang/cmake/caches/DistributionExample-stage2.cmake". This is modified
# to build Pic32Clang, such as by having it build support for MIPS devices and by
# adding extra tools not in the original file.


set(LLVM_ENABLE_PROJECTS "clang;clang-tools-extra;lld" CACHE STRING "")
set(LLVM_ENABLE_RUNTIMES "compiler-rt;libcxx;libcxxabi" CACHE STRING "")

set(LLVM_TARGETS_TO_BUILD X86;ARM;Mips CACHE STRING "")

set(CMAKE_BUILD_TYPE RelWithDebInfo CACHE STRING "")
set(CMAKE_C_FLAGS_RELWITHDEBINFO "-O3 -gline-tables-only -DNDEBUG" CACHE STRING "")
set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "-O3 -gline-tables-only -DNDEBUG" CACHE STRING "")

# setup toolchain
set(LLVM_INSTALL_TOOLCHAIN_ONLY ON CACHE BOOL "")
set(LLVM_TOOLCHAIN_TOOLS
  dsymutil
  llvm-cov
  llvm-objcopy
  llvm-dwarfdump
  llvm-profdata
  llvm-objdump
  llvm-nm
  llvm-size
  CACHE STRING "")

set(LLVM_DISTRIBUTION_COMPONENTS
  clang
  LTO
  clang-format
  clang-resource-headers
  clang-tidy
  builtins
  runtimes
  ${LLVM_TOOLCHAIN_TOOLS}
  CACHE STRING "")