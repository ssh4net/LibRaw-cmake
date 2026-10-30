# - Find LCMS2
# Find the LCMS2 includes and library
# This module defines
#  LCMS2_INCLUDE_DIR, where to find lcms.h
#  LCMS2_LIBRARIES, the libraries needed to use LCMS2.
#  LCMS2_VERSION, The value of LCMS_VERSION defined in lcms.h
#  LCMS2_FOUND, If false, do not try to use LCMS2.


# Copyright (c) 2008, Adrian Page, <adrian@pagenet.plus.com>
# Copyright (c) 2009, Cyrille Berger, <cberger@cberger.net>
#
# Redistribution and use is allowed according to the terms of the BSD license.
# For details see the accompanying LICENSE file.


# use pkg-config to get the directories and then use these values
# in the FIND_PATH() and FIND_LIBRARY() calls
if(NOT WIN32)
   find_package(PkgConfig)
   if(PKG_CONFIG_FOUND)
      pkg_check_modules(PC_LCMS2 lcms2)
      set(LCMS2_DEFINITIONS ${PC_LCMS2_CFLAGS_OTHER})
   endif()
endif(NOT WIN32)

find_path(LCMS2_INCLUDE_DIR lcms2.h
   PATHS
   ${PC_LCMS2_INCLUDEDIR}
   ${PC_LCMS2_INCLUDE_DIRS}
   PATH_SUFFIXES lcms2 liblcms2
)

# Keep an explicitly supplied LCMS2_LIBRARIES value, including link keyword
# lists. Otherwise discover both configurations for multi-config generators.
if(NOT LCMS2_LIBRARIES)
   set(_lcms2_names lcms2 liblcms2 lcms-2 liblcms-2 lcms2_static liblcms2_static)
   if(WIN32 AND DEFINED BUILD_SHARED_LIBS AND NOT BUILD_SHARED_LIBS)
      # Fresh discovery prefers an explicit static name over a DLL import
      # library. Cached choices and explicit LCMS2_LIBRARIES remain untouched.
      list(INSERT _lcms2_names 0 lcms2_static liblcms2_static)
   endif()
   set(_lcms2_debug_names)
   foreach(_lcms2_name IN LISTS _lcms2_names)
      if(CMAKE_DEBUG_POSTFIX)
         list(APPEND _lcms2_debug_names "${_lcms2_name}${CMAKE_DEBUG_POSTFIX}")
      endif()
      list(APPEND _lcms2_debug_names "${_lcms2_name}d")
   endforeach()
   find_library(LCMS2_LIBRARY_RELEASE NAMES ${_lcms2_names}
      PATHS ${PC_LCMS2_LIBDIR} ${PC_LCMS2_LIBRARY_DIRS}
      PATH_SUFFIXES lcms2
   )
   find_library(LCMS2_LIBRARY_DEBUG NAMES ${_lcms2_debug_names} ${_lcms2_names}
      PATHS ${PC_LCMS2_LIBDIR} ${PC_LCMS2_LIBRARY_DIRS}
      PATH_SUFFIXES lcms2
   )
   include(SelectLibraryConfigurations)
   select_library_configurations(LCMS2)
endif()

if(LCMS2_INCLUDE_DIR AND LCMS2_LIBRARIES)
   set(LCMS2_FOUND TRUE)
else(LCMS2_INCLUDE_DIR AND LCMS2_LIBRARIES)
   set(LCMS2_FOUND FALSE)
endif(LCMS2_INCLUDE_DIR AND LCMS2_LIBRARIES)

if(LCMS2_FOUND)
   file(READ "${LCMS2_INCLUDE_DIR}/lcms2.h" LCMS2_VERSION_CONTENT)
   string(REGEX MATCH "#define[ \t]+LCMS_VERSION[ \t]+([0-9]+)" LCMS2_VERSION_MATCH "${LCMS2_VERSION_CONTENT}")
   if(LCMS2_VERSION_MATCH)
      set(LCMS2_VERSION "${CMAKE_MATCH_1}")
      if(NOT LCMS2_FIND_QUIETLY)
         string(SUBSTRING ${LCMS2_VERSION} 0 1 LCMS2_MAJOR_VERSION)
         string(SUBSTRING ${LCMS2_VERSION} 1 2 LCMS2_MINOR_VERSION)
         message(STATUS "Found lcms version ${LCMS2_MAJOR_VERSION}.${LCMS2_MINOR_VERSION}, ${LCMS2_LIBRARIES}")
      endif(NOT LCMS2_FIND_QUIETLY)
   else(LCMS2_VERSION_MATCH)
      if(NOT LCMS2_FIND_QUIETLY)
         message(STATUS "Found lcms2 but failed to find version ${LCMS2_LIBRARIES}")
      endif(NOT LCMS2_FIND_QUIETLY)
      set(LCMS2_VERSION NOTFOUND)
   endif(LCMS2_VERSION_MATCH)
else(LCMS2_FOUND)
   if(NOT LCMS2_FIND_QUIETLY)
      if(LCMS2_FIND_REQUIRED)
         message(FATAL_ERROR "Required package lcms2 NOT found")
      else(LCMS2_FIND_REQUIRED)
         message(STATUS "lcms2 NOT found")
      endif(LCMS2_FIND_REQUIRED)
   endif(NOT LCMS2_FIND_QUIETLY)
endif(LCMS2_FOUND)

mark_as_advanced(LCMS2_INCLUDE_DIR LCMS2_LIBRARIES LCMS2_LIBRARY_RELEASE LCMS2_LIBRARY_DEBUG LCMS2_VERSION)

