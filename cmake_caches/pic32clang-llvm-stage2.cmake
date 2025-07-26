# This file sets up a CMakeCache for the second stage of a simple distribution
# bootstrap build.
#
# This is based on an example cache file provided by Clang and originally came
# from "llvm/clang/cmake/caches/DistributionExample-stage2.cmake". This is modified
# to build Pic32Clang, such as by having it build support for MIPS devices and by
# adding extra tools and options not in the original file.
#
# The original example file did not have a copyright or license notice, but
# Clang is covered under a modified Apache 2.0 license. Presumably, that
# includes the example code and so this will follow suit. A copy of the
# license is provided in LICENSE.txt.

set(LLVM_ENABLE_PROJECTS "clang;clang-tools-extra;lld;lldb;polly" CACHE STRING "")
set(LLVM_ENABLE_RUNTIMES "" CACHE STRING "")

set(LLVM_TARGETS_TO_BUILD host;ARM;Mips CACHE STRING "")

# Add targets to build documentation using the Sphinx document generator if LLVM_BUILD_DOCS is ON.
if(LLVM_BUILD_DOCS  OR  BOOTSTRAP_LLVM_BUILD_DOCS)
  set(LLVM_INCLUDE_DOCS ON CACHE BOOL "")
  set(LLVM_ENABLE_SPHINX ON CACHE BOOL "")
  set(SPHINX_WARNINGS_AS_ERRORS OFF CACHE BOOL "")
  set(SPHINX_OUTPUT_HTML ON CACHE BOOL "")
  set(SPHINX_OUTPUT_MAN ON CACHE BOOL "")
else()
  set(LLVM_INCLUDE_DOCS OFF CACHE BOOL "")
  set(LLVM_ENABLE_SPHINX OFF CACHE BOOL "")
endif()

# Build just the builtins for now. These and the rest of the runtime libraries need
# to be built separately due to errors found when running CMake compiler tests. The
# root cause appears to be Clang complaining it can't find these libraries because
# that is what we were trying to build.
set(COMPILER_RT_DEFAULT_TARGET_ONLY ON CACHE BOOL "")
set(COMPILER_RT_BUILD_SANITIZERS OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_XRAY OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_LIBFUZZER OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_PROFILE OFF CACHE BOOL "")
set(COMPILER_RT_BUILD_MEMPROF OFF CACHE BOOL "")

# Stuff that helps improve build times, mostly for debug builds.
set(LLVM_OPTIMIZED_TABLEGEN ON CACHE BOOL "")
set(LLVM_USE_SPLIT_DWARF ON CACHE BOOL "")

# Clang normally defaults to looking for GNU tools like ld or libgcc instead of
# LLVM ones like lld or compiler-rt, so change that.
set(CLANG_DEFAULT_LINKER "lld" CACHE STRING "")
set(CLANG_DEFAULT_CXX_STDLIB "libc++" CACHE STRING "")
set(CLANG_DEFAULT_RTLIB "compiler-rt" CACHE STRING "")
set(CLANG_DEFAULT_UNWINDLIB "libunwind" CACHE STRING "")
set(CLANG_DEFAULT_OBJCOPY "llvm-objcopy" CACHE STRING "")

# Tell Clang to look in ../config relative to its executable for our device
# configuration files. This can be overridden using the --config-system-dir=
# option.
set(CLANG_CONFIG_FILE_SYSTEM_DIR "../config" CACHE STRING "")

# Setup toolchain
# These are names of subdirectories under "llvm/llvm/tools".
set(LLVM_INSTALL_TOOLCHAIN_ONLY ON CACHE BOOL "")
set(LLVM_TOOLCHAIN_TOOLS
  bugpoint
  dsymutil
  llc
  llvm-ar
  llvm-config
  llvm-cov
  llvm-cxxfilt
  llvm-dwarfdump
  llvm-lto
  llvm-lto2
  llvm-mc
  llvm-nm
  llvm-objcopy
  llvm-objdump
  llvm-profdata
  llvm-profgen
  llvm-ranlib
  llvm-readelf
  llvm-readobj
  llvm-remarkutil
  llvm-size
  llvm-strings
  llvm-symbolizer
  opt
  CACHE STRING "")

set(LLVM_DISTRIBUTION_COMPONENTS
  clang
  lld
  liblldb
  lldb
  lldb-dap
  lldb-python-scripts
  LTO
  clang-apply-replacements
  clang-doc
  clang-format
  clang-resource-headers
  clang-include-fixer
  clang-refactor
  clang-scan-deps
  clang-tidy
  find-all-symbols
  clangd
  Remarks
  ${LLVM_TOOLCHAIN_TOOLS}
  CACHE STRING "")
