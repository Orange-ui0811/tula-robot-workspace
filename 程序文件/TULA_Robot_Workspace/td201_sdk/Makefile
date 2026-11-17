# Windows x64 GCC tasks equivalent to .vscode/tasks.json.
# Run from the project root, or use make -C <project-root>.
CC = gcc
CFLAGS ?= -fdiagnostics-color=always -g
SDK_SRCS := hardware/src/td201.c hardware/src/tula50.c
SDK_HEADERS := hardware/include/td201.h hardware/include/tula50.h

.PHONY: all dll c-test
all: dll

dll: $(SDK_SRCS) $(SDK_HEADERS)
	$(CC) $(CFLAGS) -shared -Ihardware/include $(SDK_SRCS) -o hardware/libs/td201.dll "-Wl,--out-implib,hardware/libs/libtd201.a"

c-test: tests/test_hardware_c.c $(SDK_SRCS) $(SDK_HEADERS)
	$(CC) $(CFLAGS) -Ihardware/include tests/test_hardware_c.c $(SDK_SRCS) -o tests/test_hardware_c.exe
