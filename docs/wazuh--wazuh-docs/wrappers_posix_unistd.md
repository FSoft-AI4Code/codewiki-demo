# wrappers_posix_unistd

## Introduction

`wrappers_posix_unistd` is Wazuh unit-test infrastructure for replacing selected POSIX `unistd` and process/file-descriptor APIs with CMocka-controlled test doubles. It lets tests validate paths and arguments, inject return values and read buffers, avoid real delays and filesystem mutation, and make process identity deterministic.

The module is test-only. It does not provide production portability or an alternative POSIX implementation. It is used together with the shared wrapper layer described in [wrappers_common.md](wrappers_common.md) and neighboring seams such as [wrappers_posix_stat.md](wrappers_posix_stat.md), [wrappers_posix_dirent.md](wrappers_posix_dirent.md), [wrappers_posix_time.md](wrappers_posix_time.md), and [wrappers_posix_pthread.md](wrappers_posix_pthread.md).

## Scope and responsibilities

| Area | Components | Purpose |
|---|---|---|
| File removal | `__wrap_unlink`, Windows-only `wrap__unlink` | Expect a path and return a scripted result. |
| File descriptors | `__wrap_close`, `__wrap_read` | Avoid real close operations and inject bytes or `EFAULT`. |
| Process identity | `__wrap_getpid`, `__wrap_gethostname` | Stabilize process/host values and return status codes. |
| Timing | `__wrap_sleep`, `__wrap_usleep` | Prevent real waiting while preserving expectations. |
| System queries | `__wrap_sysconf` | Return a CMocka-scripted configuration value. |
| Links and access | `__wrap_readlink`, `__wrap_symlink`, `__wrap_access`, Windows-only `__wrap__access` | Control link and permission checks without touching the host filesystem. |

Implementation: `src/unit_tests/wrappers/posix/unistd_wrappers.c`. Its declarations are supplied by the neighboring `unistd_wrappers.h` header. The source also includes `src/unit_tests/wrappers/common.h` for the shared `test_mode` flag.

## Architecture

~~~mermaid
flowchart LR
    T[Test case] -->|sets expectations and mock values| M[CMocka state]
    T --> U[Code under test]
    U -->|wrapped unistd call| W[unistd_wrappers.c]
    W -->|check_expected / mock / mock_type| M
    W -->|controlled return, copy, or no-op| U
    B[Test linker configuration] -->|redirects POSIX symbols| W
    W -. avoids .-> OS[Real process, sleep, files, links, and descriptors]
    C[wrappers_common] -->|test_mode| W
~~~

The wrapper preserves the call shape expected by production code while moving side effects into test-controlled behavior. Most wrappers return `mock()`; wrappers that need richer behavior read typed values or copy mocked data.

## Core components

### `__wrap_unlink` and `wrap__unlink`

`__wrap_unlink(const char *file)` checks the expected path with `check_expected_ptr(file)` and returns `mock()`.

On Windows builds, `wrap__unlink(const char *file)` provides the corresponding `_unlink` seam with the same behavior. The platform guard means the symbol is absent from non-Windows builds.

These functions do not remove anything. A test normally configures both the expected pointer and the result code, allowing success, permission errors, or missing-file paths to be exercised without changing the test workspace.

### `__wrap_close`

`__wrap_close(int fd)` ignores the descriptor and always returns `1`. It does not validate the descriptor, call the native `close()`, or model descriptor state. This is a deliberately minimal isolation seam for code whose cleanup path should not close a real test runner descriptor.

### `__wrap_getpid`

`__wrap_getpid()` returns `2345` when the shared `test_mode` flag is enabled. Otherwise it delegates to `__real_getpid()`, which is the linker-wrapped native implementation.

This conditional behavior makes unit tests deterministic while preserving real process identity in contexts where the wrapper is linked but test mode is disabled.

### `__wrap_sleep` and `__wrap_usleep`

On non-Windows builds, `__wrap_sleep(unsigned int seconds)` validates the requested duration with `check_expected(seconds)` and returns immediately. `__wrap_usleep(useconds_t usec)` marks the function as called with `function_called()` and returns `0`; the microsecond value is intentionally not asserted.

Neither function blocks. Tests can therefore cover retry loops and timeout branches without slowing execution. The distinction matters: `sleep()` checks its argument, while `usleep()` only verifies invocation.

### `__wrap_sysconf`

`__wrap_sysconf(int name)` ignores the query name and returns `mock()`. The test must provide the desired result, including a negative value when the code under test handles an unavailable system limit.

### `__wrap_read`

`__wrap_read(int fildes, void *buf, size_t nbyte)` obtains two typed mock values:

1. A `char *buffer` containing the bytes to expose.
2. A `size_t n` describing the available byte count.

If `buffer` is non-null, the wrapper copies `min(nbyte, n)` bytes into `buf` and returns the copied length. If `buffer` is null, it sets `errno = EFAULT` and returns `-1`.

The file descriptor is ignored. The wrapper therefore models payload length and a common bad-buffer failure, but not partial descriptor state, `EINTR`, blocking, or end-of-file beyond a zero-length mock.

~~~mermaid
flowchart TD
    R[Code calls read(fd, buf, nbyte)] --> W[__wrap_read]
    W --> V1[mock_type(char *)]
    W --> V2[mock_type(size_t)]
    V1 --> D{buffer non-null?}
    D -->|yes| L{nbyte > n?}
    L -->|yes| C1[copy n bytes; return n]
    L -->|no| C2[copy nbyte bytes; return nbyte]
    D -->|no| E[set errno=EFAULT; return -1]
~~~

The destination buffer is assumed to be valid, as it would be for the native API. Tests should provide enough storage for the configured copy size.

### `__wrap_gethostname`

`__wrap_gethostname(char *name, int len)` obtains a mocked `char *`, formats it into the caller buffer using `snprintf(name, len, "%s", ...)`, and returns a mocked `int` status code. This permits tests to independently control the returned hostname and whether the operation reports success or failure.

The wrapper relies on `snprintf` for truncation behavior. A test should provide a non-null mock string and a destination/length consistent with the intended branch.

### `__wrap_readlink`

`__wrap_readlink(void **state)` ignores its argument and returns `mock()`. The signature is intentionally aligned with the wrapper header and test build, even though it is not a conventional production `readlink(const char *, char *, size_t)` signature. Callers of this seam should follow the repository's declared wrapper contract rather than infer a native ABI from the function name.

### `__wrap_symlink`

`__wrap_symlink(const char *path1, const char *path2)` checks both path arguments with `check_expected()` and returns `mock()`. It never creates a link. Tests can therefore verify source and destination path construction separately from handling of the native return code.

### `__wrap_access` and `__wrap__access`

`__wrap_access(const char *__name, int __type)` checks the pathname and access mode, then returns `mock()`.

On Windows, `__wrap__access()` supplies the `_access` equivalent with identical behavior. These wrappers are useful for testing existence, readability, writability, and path-validation branches without depending on host permissions.

## Data flow and interaction

~~~mermaid
sequenceDiagram
    participant F as Test fixture
    participant C as CMocka
    participant P as Code under test
    participant W as unistd wrapper

    F->>C: Configure expected paths, calls, and mock values
    F->>P: Execute unit under test
    P->>W: Invoke wrapped unistd API
    alt path or mode validation
        W->>C: check_expected / check_expected_ptr
        W->>C: mock()
        C-->>W: Scripted result
    else read
        W->>C: mock_type(char *) and mock_type(size_t)
        W-->>P: Copy bounded bytes or return EFAULT
    else process and timing
        W-->>P: Deterministic PID or immediate no-op
    end
    W-->>P: Return controlled result
~~~

At link time, the test executable redirects selected native symbols to `__wrap_*` symbols. The wrapper then uses CMocka's global per-test state. No persistent module state is maintained by this source other than the externally provided `test_mode` value.

## Dependency relationships

~~~mermaid
graph TD
    H[unistd_wrappers.h] --> POSIX[unistd and platform declarations]
    C[unistd_wrappers.c] --> H
    C --> CM[cmocka.h]
    C --> STD[stddef.h / stdarg.h / setjmp.h]
    C --> STR[string.h / stdio.h]
    C --> ERR[errno contract]
    C --> COMMON[wrappers/common.h]
    COMMON --> MODE[test_mode]
    UUT[Test executable] -->|symbol wrapping| C
    UUT --> DIR[wrappers_posix_dirent]
    UUT --> STAT[wrappers_posix_stat]
    UUT --> TIME[wrappers_posix_time]
    UUT --> PTHREAD[wrappers_posix_pthread]
~~~

The sibling modules remain separate because they own different POSIX families. For example, directory enumeration belongs to [wrappers_posix_dirent.md](wrappers_posix_dirent.md), metadata and permissions to [wrappers_posix_stat.md](wrappers_posix_stat.md), and synchronization to [wrappers_posix_pthread.md](wrappers_posix_pthread.md). A test may link several seams at once, but each wrapper should be configured only for the API calls it owns.

## Process flows

### Testing a filesystem operation

~~~mermaid
flowchart LR
    A[Test prepares expected path] --> B[Test queues mock return code]
    B --> C[UUT calls unlink, symlink, or access]
    C --> D[Wrapper validates arguments]
    D --> E[Wrapper returns scripted result]
    E --> F[UUT handles success or failure]
~~~

### Testing a read path

~~~mermaid
flowchart LR
    A[Queue mocked buffer and length] --> B[UUT calls read]
    B --> C{Buffer configured?}
    C -->|yes| D[Copy bounded amount]
    D --> E[Return copied length]
    C -->|no| F[Set EFAULT]
    F --> G[Return -1]
~~~

### Testing retry or delayed code

~~~mermaid
flowchart LR
    A[UUT reaches sleep/usleep] --> B[Wrapper checks call contract]
    B --> C[Return immediately]
    C --> D[UUT continues retry/timeout branch]
~~~

## Platform behavior

| Build | Available differences |
|---|---|
| POSIX | `sleep()` and `usleep()` wrappers are compiled; `unlink`, `access`, `read`, `getpid`, `gethostname`, `readlink`, `symlink`, `sysconf`, and `close` seams are available. |
| Windows | `_unlink` and `_access` wrappers are additionally available; POSIX sleep wrappers are excluded by `#ifndef WIN32`. `getpid` uses the same test-mode logic. |

The source uses conditional compilation rather than runtime platform detection. Build/link configuration must therefore use the symbol names matching the target platform.

## Testing and maintenance guidance

- Configure every `mock()` and `mock_type()` value in the test that invokes the corresponding wrapper.
- Pair `check_expected()` or `check_expected_ptr()` with expectations in the same test fixture; otherwise argument validation can fail before the unit under test reaches its assertion.
- For `read()`, treat the mocked length as available input, not necessarily the requested length. The implementation intentionally returns the smaller of the requested and available lengths.
- Do not expect `close()`, `sleep()`, `unlink()`, `symlink()`, or access checks to affect the host. Their purpose is isolation.
- Remember that `test_mode` affects only `getpid()`. It does not automatically switch all wrappers into deterministic mode.
- When adding a new POSIX API, keep the wrapper family cohesive and update the corresponding header and test-link configuration. Cross-family behavior should be documented in the relevant sibling module.

## Summary

`wrappers_posix_unistd` is a narrow interception layer around process, timing, descriptor, link, access, and basic read APIs. Its main design pattern is: validate inputs with CMocka, inject outputs or return codes, and suppress operating-system side effects. The `read()` and `gethostname()` wrappers additionally model output buffers, while `getpid()` provides a controlled value only in shared test mode. Together with the other POSIX and external wrappers, it gives Wazuh unit tests deterministic and fast coverage of system-facing branches.
