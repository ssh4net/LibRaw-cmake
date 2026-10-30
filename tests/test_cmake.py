"""Portable CMake integration tests; no downloaded LibRaw or SDK is required."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(command: list[str], env=None, cwd=None) -> str:
    result = subprocess.run(command, capture_output=True, text=True, env=env, cwd=cwd, timeout=120)
    if result.returncode:
        raise AssertionError(" ".join(command) + "\n" + result.stdout + result.stderr)
    return result.stdout + result.stderr


def configure(source: Path, build: Path, *args: str) -> None:
    generator = []
    if not os.environ.get("CMAKE_GENERATOR") and shutil.which("ninja") and (os.name != "nt" or shutil.which("cl")):
        generator = ["-G", "Ninja"]
    build.mkdir(parents=True, exist_ok=True)
    run(["cmake", str(source), *generator,
         "-DCMAKE_EXPORT_PACKAGE_REGISTRY=OFF", "-DCMAKE_EXPORT_NO_PACKAGE_REGISTRY=ON",
         "-DCMAKE_FIND_PACKAGE_NO_PACKAGE_REGISTRY=ON",
         "-DCMAKE_FIND_PACKAGE_NO_SYSTEM_PACKAGE_REGISTRY=ON", *args], cwd=build)


def build_install(build: Path, mode: str) -> None:
    run(["cmake", "--build", str(build), "--config", mode, "--parallel", "2"])
    run(["cmake", "--build", str(build), "--target", "install", "--config", mode, "--parallel", "2"])


def fake_libraw(root: Path) -> None:
    write(root / "libraw/libraw_version.h", """#define LIBRAW_MAJOR_VERSION 0
#define LIBRAW_MINOR_VERSION 22
#define LIBRAW_PATCH_VERSION 0
#define LIBRAW_SHLIB_CURRENT 26
#define LIBRAW_SHLIB_REVISION 0
#define LIBRAW_SHLIB_AGE 0
""")
    write(root / "libraw/libraw.h", """#pragma once
#define CURRENT_LIBRAW_HEADER 1
#if defined(_WIN32) && !defined(LIBRAW_NODLL)
# ifdef LIBRAW_BUILDLIB
#  define RAW_API __declspec(dllexport)
# else
#  define RAW_API __declspec(dllimport)
# endif
#else
# define RAW_API
#endif
#ifdef USE_DNGSDK
# include <fake_dng.h>
#endif
#ifdef __cplusplus
extern "C" {
#endif
RAW_API int raw_fixture_value(void);
#ifdef __cplusplus
}
#endif
""")
    for header in ("libraw_alloc.h", "libraw_const.h", "libraw_datastream.h", "libraw_internal.h", "libraw_types.h"):
        write(root / "libraw" / header, "/* fixture */\n")
    write(root / "src/fixture.cpp", """#include <libraw/libraw.h>
#ifndef CURRENT_LIBRAW_HEADER
# error Stale prefix header was selected
#endif
int raw_fixture_value(void) {
#ifdef USE_DNGSDK
    return fake_dng_value();
#else
    return 42;
#endif
}
""")
    sample = "#include <libraw/libraw.h>\nint main(void) { return raw_fixture_value() == 42 ? 0 : 1; }\n"
    for name in ("simple_dcraw", "mem_image_sample", "dcraw_emu", "4channels", "unprocessed_raw",
                 "raw-identify", "rawtextdump", "openbayer_sample", "multirender_test", "postprocessing_benchmark"):
        write(root / "samples" / (name + ".cpp"), sample)
    for name in ("dcraw_half", "half_mt", "half_mt_win32"):
        write(root / "samples" / (name + ".c"), sample)
    for name in ("COPYRIGHT", "LICENSE.CDDL", "LICENSE.LGPL", "Changelog.txt"):
        write(root / name, "fixture\n")


def fake_sdk(source: Path, build: Path, prefix: Path, mode: str) -> None:
    write(source / "include/fake_dng.h", """#pragma once
#ifndef FAKE_DNG_TRANSITIVE
# error SDK compile requirements were not propagated
#endif
#if defined(_WIN32) && !defined(NOMINMAX)
# error Windows DNG consumers need NOMINMAX
#endif
#ifdef __cplusplus
extern "C" {
#endif
int fake_dng_value(void);
#ifdef __cplusplus
}
#endif
""")
    write(source / "include/lcms2.h", "#define LCMS_VERSION 2200\n")
    write(source / "sdk.c", '#include "fake_dng.h"\nint fake_dependency(void);\nint fake_dng_value(void) { return fake_dependency(); }\n')
    write(source / "dep.c", "int fake_dependency(void) { return 42; }\n")
    write(source / "lcms.c", "int fake_lcms(void) { return 0; }\n")
    write(source / "CMakeLists.txt", """cmake_minimum_required(VERSION 3.12)
project(fake_sdk C)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
add_library(fake_dependency STATIC dep.c)
add_library(fake_sdk STATIC sdk.c)
set_target_properties(fake_sdk PROPERTIES EXPORT_NAME dng_sdk)
target_compile_definitions(fake_sdk PUBLIC FAKE_DNG_TRANSITIVE=1 PRIVATE NOMINMAX)
target_include_directories(fake_sdk PUBLIC
  "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>" "$<INSTALL_INTERFACE:include>")
target_link_libraries(fake_sdk PUBLIC fake_dependency)
add_library(fake_lcms STATIC lcms.c)
set_target_properties(fake_lcms PROPERTIES OUTPUT_NAME lcms2_static DEBUG_POSTFIX d)
install(TARGETS fake_sdk fake_dependency EXPORT sdkTargets ARCHIVE DESTINATION lib)
install(TARGETS fake_lcms ARCHIVE DESTINATION lib)
install(DIRECTORY include/ DESTINATION include)
install(EXPORT sdkTargets NAMESPACE dng_sdk:: FILE dng_sdk-targets.cmake DESTINATION lib/cmake/dng_sdk)
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/dng_sdk-config.cmake"
  "include(\"\\${CMAKE_CURRENT_LIST_DIR}/dng_sdk-targets.cmake\")\\n")
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/dng_sdk-config.cmake" DESTINATION lib/cmake/dng_sdk)
""")
    configure(source, build, f"-DCMAKE_BUILD_TYPE={mode}", f"-DCMAKE_INSTALL_PREFIX={prefix}")
    build_install(build, mode)


@unittest.skipUnless(shutil.which("cmake"), "CMake is required")
class CMakeIntegrationTests(unittest.TestCase):
    def _package_case(self, *, samples: bool, shared: bool, sdk: bool, mode: str = "Release") -> None:
        with tempfile.TemporaryDirectory(prefix="libraw cmake ") as tmp:
            root = Path(tmp)
            raw = root / "external LibRaw"
            fake_libraw(raw)
            sdk_prefix = root / "SDK prefix"
            if sdk:
                fake_sdk(root / "SDK source", root / "SDK build", sdk_prefix, mode)
            stale = root / "stale prefix/include"
            write(stale / "libraw/libraw.h", "#error Installed stale LibRaw header must not be used\n")
            source = root / "parent project"
            write(source / "CMakeLists.txt", """cmake_minimum_required(VERSION 3.12)
project(parent CXX)
find_package(Threads REQUIRED)
include_directories("${STALE_INCLUDE}")
add_subdirectory("${LIBRAW_CMAKE}" libraw)
get_property(languages GLOBAL PROPERTY ENABLED_LANGUAGES)
if(NOT ENABLE_EXAMPLES AND "C" IN_LIST languages)
  message(FATAL_ERROR "Library-only configuration unexpectedly enabled C")
endif()
""")
            build = root / "build"
            prefix = root / "install"
            configure(source, build, f"-DLIBRAW_CMAKE={ROOT.as_posix()}", f"-DLIBRAW_PATH={raw.as_posix()}",
                      f"-DSTALE_INCLUDE={stale.as_posix()}", f"-DCMAKE_BUILD_TYPE={mode}",
                      f"-DCMAKE_INSTALL_PREFIX={prefix.as_posix()}", "-DCMAKE_INSTALL_LIBDIR=lib",
                      "-DLIBRAW_INSTALL=ON",
                      f"-DBUILD_SHARED_LIBS={'ON' if shared else 'OFF'}", f"-DENABLE_EXAMPLES={'ON' if samples else 'OFF'}",
                      "-DENABLE_OPENMP=OFF", f"-DENABLE_LCMS={'ON' if sdk else 'OFF'}", "-DENABLE_JASPER=OFF",
                      "-DCMAKE_DISABLE_FIND_PACKAGE_ZLIB=ON", "-DCMAKE_DISABLE_FIND_PACKAGE_JPEG=ON",
                      f"-DENABLE_DNGSDK={'ON' if sdk else 'OFF'}", f"-DDNGSDK_ROOT={sdk_prefix.as_posix()}",
                      f"-DCMAKE_PREFIX_PATH={sdk_prefix.as_posix()}")
            build_install(build, mode)
            env = dict(os.environ)
            env["PATH"] = str(prefix / "bin") + os.pathsep + env.get("PATH", "")
            for variable in ("LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
                env[variable] = str(prefix / "lib") + os.pathsep + env.get(variable, "")
            if samples:
                sample_name = "half_mt_win32" if os.name == "nt" else "dcraw_half"
                binary = prefix / "bin" / (sample_name + (".exe" if os.name == "nt" else ""))
                run([str(binary)], env)
            consumer = root / "consumer"
            write(consumer / "main.cpp", "#include <libraw.h>\nint main() { return raw_fixture_value() == 42 ? 0 : 1; }\n")
            write(consumer / "CMakeLists.txt", """cmake_minimum_required(VERSION 3.12)
project(consumer CXX)
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/sentinel")
find_package(libraw CONFIG REQUIRED)
if(NOT CMAKE_MODULE_PATH STREQUAL "${CMAKE_CURRENT_SOURCE_DIR}/sentinel")
  message(FATAL_ERROR "libraw package leaked its module path")
endif()
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE libraw::raw)
""")
            consumer_build = root / "consumer build"
            configure(consumer, consumer_build, f"-DCMAKE_BUILD_TYPE={mode}",
                      f"-DCMAKE_PREFIX_PATH={prefix.as_posix()};{sdk_prefix.as_posix()}")
            run(["cmake", "--build", str(consumer_build), "--config", mode, "--parallel", "2"])
            executable = consumer_build / ("consumer.exe" if os.name == "nt" else "consumer")
            if not executable.exists():
                executable = consumer_build / mode / executable.name
            run([str(executable)], env)
            if not samples:
                # Older callers can retain their explicit package-directory hint.
                legacy_build = root / "legacy consumer build"
                configure(consumer, legacy_build, f"-DCMAKE_BUILD_TYPE={mode}",
                          f"-Dlibraw_DIR={prefix.as_posix()}/lib/cmake")
                run(["cmake", "--build", str(legacy_build), "--config", mode, "--parallel", "2"])
            pc = (prefix / "lib/pkgconfig/libraw.pc").read_text()
            self.assertEqual(sdk, " dng_sdk" in pc)
            self.assertEqual(sdk, "-DUSE_DNGSDK" in pc)

    def test_cpp_only_library_without_sdk(self):
        self._package_case(samples=False, shared=False, sdk=False)

    def test_shared_library_and_c_samples_without_sdk(self):
        self._package_case(samples=True, shared=True, sdk=False)

    def test_static_sdk_transitive_dependencies_and_installed_consumers(self):
        for mode in ("Debug", "Release"):
            with self.subTest(mode=mode):
                self._package_case(samples=True, shared=False, sdk=True, mode=mode)

    def test_lcms_windows_static_names_configurations_and_explicit_override(self):
        with tempfile.TemporaryDirectory(prefix="lcms finder ") as tmp:
            root = Path(tmp)
            prefix = root / "prefix"
            write(prefix / "include/lcms2.h", "#define LCMS_VERSION 2200\n")
            for name in ("lcms2.lib", "lcms2_dbg.lib", "lcms2_static.lib", "lcms2_static_dbg.lib", "custom.lib"):
                write(prefix / "lib" / name, "fixture library\n")
            source = root / "source"
            write(source / "CMakeLists.txt", """cmake_minimum_required(VERSION 3.12)
project(lcms_names NONE)
set(WIN32 TRUE)
set(CMAKE_FIND_LIBRARY_PREFIXES "")
set(CMAKE_FIND_LIBRARY_SUFFIXES .lib)
set(CMAKE_DEBUG_POSTFIX _dbg)
list(INSERT CMAKE_MODULE_PATH 0 "${LIBRAW_CMAKE}/cmake/modules")
find_package(LCMS2 REQUIRED)
if(OVERRIDE)
  if(NOT LCMS2_LIBRARIES STREQUAL "${TEST_PREFIX}/lib/custom.lib")
    message(FATAL_ERROR "Explicit LCMS2_LIBRARIES was replaced")
  endif()
else()
  if(NOT LCMS2_LIBRARY_RELEASE STREQUAL "${TEST_PREFIX}/lib/${EXPECTED_NAME}.lib" OR
     NOT LCMS2_LIBRARY_DEBUG STREQUAL "${TEST_PREFIX}/lib/${EXPECTED_NAME}_dbg.lib")
    message(FATAL_ERROR "Wrong LCMS2 configurations: ${LCMS2_LIBRARIES}")
  endif()
endif()
""")
            for override, shared, expected in ((False, "OFF", "lcms2_static"),
                                               (False, "ON", "lcms2"), (True, "OFF", "custom")):
                args = [f"-DLIBRAW_CMAKE={ROOT.as_posix()}", f"-DTEST_PREFIX={prefix.as_posix()}",
                        f"-DCMAKE_PREFIX_PATH={prefix.as_posix()}", "-DCMAKE_BUILD_TYPE=Debug",
                        f"-DBUILD_SHARED_LIBS={shared}", f"-DEXPECTED_NAME={expected}"]
                if override:
                    args += ["-DOVERRIDE=ON", f"-DLCMS2_LIBRARIES={prefix.as_posix()}/lib/custom.lib"]
                configure(source, root / ("override" if override else "discovery-" + shared), *args)

    def test_missing_lcms_dependency_does_not_leak_module_path(self):
        with tempfile.TemporaryDirectory(prefix="lcms missing ") as tmp:
            root = Path(tmp)
            write(root / "CMakeLists.txt", """cmake_minimum_required(VERSION 3.12)
project(dependency_scope NONE)
include(CMakePackageConfigHelpers)
set(LCMS_SUPPORT_CAN_BE_COMPILED TRUE)
set(LCMS2_FOUND TRUE)
configure_package_config_file("${LIBRAW_CMAKE}/cmake/librawConfig.cmake.in"
  "${CMAKE_BINARY_DIR}/package/librawConfig.cmake" INSTALL_DESTINATION lib/cmake/libraw)
unset(LCMS2_FOUND)
set(libraw_DIR "${CMAKE_BINARY_DIR}/package")
set(CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/sentinel")
set(CMAKE_DISABLE_FIND_PACKAGE_LCMS2 TRUE)
find_package(libraw QUIET CONFIG)
if(libraw_FOUND)
  message(FATAL_ERROR "libraw succeeded without its required LCMS dependency")
endif()
if(NOT CMAKE_MODULE_PATH STREQUAL "${CMAKE_CURRENT_SOURCE_DIR}/sentinel")
  message(FATAL_ERROR "Missing dependency leaked the private finder path")
endif()
""")
            configure(root, root / "build", f"-DLIBRAW_CMAKE={ROOT.as_posix()}")


if __name__ == "__main__":
    unittest.main()
