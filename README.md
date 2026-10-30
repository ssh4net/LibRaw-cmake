LibRaw-cmake
============

[![Build Status](https://travis-ci.org/LibRaw/LibRaw-cmake.svg?branch=master)](https://travis-ci.org/LibRaw/LibRaw-cmake)

This is a separate repository for LibRaw CMake support scripts.
It is [unmaintained](https://github.com/LibRaw/LibRaw/issues/44#issuecomment-60344793) by the authors of LibRaw and relies solely on user contributions.
The current community-maintainer of this repository is [Maik Riechert](https://github.com/neothemachine).

If you wish to contribute to it, please open an issue or submit a pull request in this repository. Do *not* submit issues or pull requests regarding CMake to the main [LibRaw repository](https://github.com/LibRaw/LibRaw). Also, try to keep CMake related discussions out of the [main forum](http://www.libraw.org/forum), instead use the issues for that.

If you like to become a direct contributor with write permissions to this repository, please contact the [LibRaw authors](https://github.com/LibRaw).

How to use
----------
Just copy the contents of this repository into the root LibRaw folder and run cmake as usual.

### Add as a submodule

Add this repo and libraw as git submodules:

`git submodule add https://github.com/LibRaw/LibRaw-cmake.git`

`git submodule add https://github.com/LibRaw/LibRaw.git`

In your CMakeLists.txt add 

```cmake
add_subdirectory(LibRaw-cmake)
target_link_libraries(ProjectName PRIVATE libraw::libraw)
```

Set the `LIBRAW_PATH` CMake variable to point to the **LibRaw** directory:

`cmake -DLIBRAW_PATH=./LibRaw/`

### Optional Adobe DNG SDK integration

`ENABLE_DNGSDK` defaults to `OFF`. Enable it with an installed SDK package that
provides the `dng_sdk::dng_sdk` CMake target:

```sh
mkdir build
cd build
cmake /path/to/LibRaw-cmake -DLIBRAW_PATH=/path/to/LibRaw \
  -DENABLE_DNGSDK=ON -DDNGSDK_ROOT=/path/to/sdk-prefix
cmake --build . --config Release
```

The imported SDK target supplies its headers, compile definitions and transitive
libraries to both LibRaw libraries and their consumers. Windows DNG builds also
propagate `NOMINMAX`. Installed CMake consumers must make the SDK package
available through `CMAKE_PREFIX_PATH` or `dng_sdk_DIR`. Static pkg-config consumers
need the SDK's `dng_sdk.pc` and its dependencies on `PKG_CONFIG_PATH`.

Examples enable the C language as well as C++; `ENABLE_EXAMPLES=OFF` keeps a
library-only build compatible with a C++-only toolchain. LCMS2 discovery supports
Windows static library names, Debug/Release variants and an explicit
`LCMS2_LIBRARIES` override.
Discovery follows the normal CMake cache rules: clear `LCMS2_LIBRARY_RELEASE`
and `LCMS2_LIBRARY_DEBUG` when changing the automatic dependency choice, or set
`LCMS2_LIBRARIES` explicitly.

Installed CMake consumers can use `find_package(libraw CONFIG REQUIRED)` with
the install prefix in `CMAKE_PREFIX_PATH`, then link `libraw::raw` or
`libraw::raw_r`. Package files live in `lib/cmake/libraw` (under the selected
`CMAKE_INSTALL_LIBDIR`); forwarding files preserve the previous explicit
`libraw_DIR=<prefix>/lib/cmake` location.

### Integration tests

Run `python -m unittest discover -s tests -v` with CMake and a C/C++ compiler
available. The tests create small local fixtures, build static/shared libraries
and C examples, and compile installed consumers with optional SDK dependencies.
They also check source-header precedence and Windows LCMS2 library naming.
Use a Visual Studio Developer Prompt for Ninja/MSVC tests on Windows.
