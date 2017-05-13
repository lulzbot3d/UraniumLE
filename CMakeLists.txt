project(uranium NONE)

cmake_minimum_required(VERSION 2.8.12)

message(STATUS ${CMAKE_MODULE_PATH})

set(CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake/
                      ${CMAKE_MODULE_PATH})
include(UraniumTranslationTools)

include(GNUInstallDirs)

if (NOT MINIMUM_PYTHON_VERSION)
    set(MINIMUM_PYTHON_VERSION 3.5.0)
endif()

set(MINIMUM_PYTHON_VERSION ${MINIMUM_PYTHON_VERSION} CACHE STRING "Minimum Python Version")

if (NOT BUILD_PYTHON)
    find_package(PythonInterp ${MINIMUM_PYTHON_VERSION} REQUIRED)
endif()

# # Checks using pylint
# Note that we use exit 0 here to not mark the build as a failure on check failure
# In addition, the specified pylint configuration uses the spellchecker plugin. This required python-enchant to be installed.
add_custom_target(check)
add_custom_command(TARGET check POST_BUILD COMMAND "PYTHONPATH=${CMAKE_SOURCE_DIR}" ${PYTHON_EXECUTABLE} -m pylint --rcfile=${CMAKE_SOURCE_DIR}/pylint.cfg UM --msg-template=\"{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}\" > ${CMAKE_BINARY_DIR}/pylint.log || exit 0 WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# # Check using Mypy
add_custom_target(typecheck)
add_custom_command(TARGET typecheck POST_BUILD COMMAND ${PYTHON_EXECUTABLE} run_mypy.py WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})

# # Tests
enable_testing()
add_test(NAME pytest COMMAND ${PYTHON_EXECUTABLE} -m pytest -r a --junitxml=${CMAKE_BINARY_DIR}/junit.xml ${CMAKE_SOURCE_DIR})
# Using untranslated strings on Linux
if(UNIX AND NOT APPLE) 
    set_tests_properties(pytest PROPERTIES ENVIRONMENT LANG=C)
endif()
# Adding PYTHONPATH on every OS
set_tests_properties(pytest PROPERTIES ENVIRONMENT PYTHONPATH=${CMAKE_SOURCE_DIR})
# Adding compatibility with our old tests target
add_custom_target(tests
                  COMMAND ${CMAKE_COMMAND} --build ${CMAKE_BINARY_DIR} --target test
                  COMMENT "Notice: tests target is deprecated, please use the test target")

# # Benchmarks
# add_custom_target(benchmark)
# file(GLOB bench_files tests/benchmarks/*/profile*.py)
# foreach(file ${bench_files})
#     add_custom_command(TARGET benchmark POST_BUILD COMMAND "PYTHONPATH=${CMAKE_SOURCE_DIR}" kernprof ARGS -l -v ${file})
# endforeach()


# Documentation
find_package(Doxygen)
if(${DOXYGEN_FOUND})
    add_custom_target(doc ${DOXYGEN_EXECUTABLE} ${CMAKE_SOURCE_DIR}/Doxyfile WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
endif()

# Extract Strings
add_custom_target(extract-messages ${CMAKE_SOURCE_DIR}/scripts/extract-messages ${CMAKE_SOURCE_DIR} uranium)

# Build Translations
CREATE_TRANSLATION_TARGETS()

if(NOT PYTHON_SITE_PACKAGES_DIR)
	if(APPLE OR WIN32)
		set(PYTHON_SITE_PACKAGES_DIR lib/python${PYTHON_VERSION_MAJOR}.${PYTHON_VERSION_MINOR}/site-packages
			CACHE STRING "Directory to install Python bindings to")
	else()
		set(PYTHON_SITE_PACKAGES_DIR lib/python${PYTHON_VERSION_MAJOR}/dist-packages CACHE
			STRING "Directory to install Python bindings to")
	endif()
	set(URANIUM_INSTALL_MODULES_PATH 
		${CMAKE_INSTALL_DATADIR}/cmake-${CMAKE_MAJOR_VERSION}.${CMAKE_MINOR_VERSION}/Modules/ )
	set(URANIUM_INSTALL_PLUGINS_PATH 
		lib/uranium)
else()
	set(URANIUM_INSTALL_MODULES_PATH ${CMAKE_INSTALL_DATADIR}/cmake/Modules/)
	set(URANIUM_INSTALL_PLUGINS_PATH ${CMAKE_INSTALL_LIBDIR}/uranium )
endif()
install(DIRECTORY UM DESTINATION ${PYTHON_SITE_PACKAGES_DIR})

install(FILES ${CMAKE_SOURCE_DIR}/cmake/UraniumTranslationTools.cmake DESTINATION ${URANIUM_INSTALL_MODULES_PATH})
install(DIRECTORY resources DESTINATION ${CMAKE_INSTALL_DATADIR}/uranium)
install(DIRECTORY plugins DESTINATION ${URANIUM_INSTALL_PLUGINS_PATH} )

include(CPackConfig.cmake)
