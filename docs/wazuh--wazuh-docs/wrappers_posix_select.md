# wrappers_posix_select

## Introduction

`wrappers_posix_select` is Wazuh unit-test infrastructure for replacing the POSIX `select()` system call with a deterministic CMocka-controlled implementation. It provides a linker/test seam for code that waits on file descriptors, allowing tests to exercise ready, timeout, and error paths without blocking on real descriptors or depending on operating-system timing.

This is test-only infrastructure. It has no production event loop, socket ownership, persistent state, or standalone executable. Related operating-system seams are documented in [wrappers_linux_socket.md](wrappers_linux_socket.md) and [wrappers_posix_pthread.md](wrappers_posix_pthread.md).

## Scope and responsibilities

| Component | Location | Responsibility |
|---|---|---|
| Select wrapper implementation | `src/unit_tests/wrappers/posix/select_wrappers.c` | Implements `__wrap_select()` and returns the next value supplied by CMocka. |
| Wrapper interface | `src/unit_tests/wrappers/posix/select_wrappers.h` | Includes the POSIX `select()` declarations and exposes the wrapper prototype. |
| POSIX select types | `<sys/select.h>` | Supplies `fd_set`, `struct timeval`, and the native `select()`-compatible types. |
| Mock controller | `<cmocka.h>` | Supplies `mock()`, which determines the wrapper's return value. |

Both files are enclosed by `#ifndef WIN32`. The wrapper is compiled and declared only for non-Windows targets, because this module models a POSIX API.

## Architecture

~~~mermaid
flowchart LR
    Test[Test case / fixture] -->|queues return value| CMocka[CMocka mock state]
    Test --> SUT[Code under test]
    SUT -->|wrapped select symbol| W[select_wrappers.c]
    W -->|mock()| CMocka
    W -->|returns int| SUT
    H[select_wrappers.h] --> POSIX[sys/select.h]
    W --> H
    Build[Test linker / symbol wrapping] -->|redirects select calls| W
~~~

The seam preserves the call shape expected by the system under test, but does not perform descriptor polling. The descriptor sets and timeout are accepted for interface compatibility and ignored by the implementation. Test setup controls only the integer result returned by `mock()`.

## Public interface

### `__wrap_select`

~~~c
int __wrap_select(int nfds,
                  fd_set *restrict readfds,
                  fd_set *restrict writefds,
                  fd_set *restrict errorfds,
                  struct timeval *restrict timeout);
~~~

The prototype mirrors the POSIX `select()` interface:

- `nfds` is the descriptor-number boundary used by native `select()`.
- `readfds`, `writefds`, and `errorfds` identify descriptor sets in native code.
- `timeout` points to the native `struct timeval` timeout value.

The wrapper marks all arguments as unused and does not inspect, mutate, or dereference them.

### `timeval`

`timeval` in the module tree refers to the POSIX `struct timeval` type imported through `<sys/select.h>`. The wrapper header does not define a replacement structure and does not add helper functions for timeout construction or inspection.

## Implementation behavior

`__wrap_select()` has one behavior: it returns `mock()`.

~~~c
int __wrap_select(..., struct timeval *restrict timeout) {
    return mock();
}
~~~

Consequences of this design:

- The wrapper never calls the real `select()` implementation.
- No file descriptor is examined or marked ready.
- `nfds`, all three `fd_set` pointers, and `timeout` have no effect on the result.
- The return value is entirely controlled by the CMocka mock queue.
- The wrapper does not modify `fd_set` contents or the pointed-to `timeval`.
- The wrapper does not itself set `errno`, sleep, allocate memory, or close descriptors.

The test must therefore model any expected post-call descriptor-set state itself if the caller inspects those sets after `select()` returns. In particular, a positive mocked return value does not identify which descriptor became ready.

## Data flow and component interaction

~~~mermaid
sequenceDiagram
    participant F as Test fixture
    participant M as CMocka
    participant P as Code under test
    participant W as __wrap_select

    F->>M: Queue integer return value
    P->>W: select(nfds, readfds, writefds, errorfds, timeout)
    W->>M: mock()
    M-->>W: Scripted int
    W-->>P: Return scripted int
    P->>P: Follow ready / timeout / error branch
~~~

The wrapper is a pure result injection point. It does not create a realistic readiness event; callers that need one should prepare their own fixture state or use a more specialized test seam.

## Dependency relationships

~~~mermaid
graph TD
    H[select_wrappers.h] --> SYS[sys/select.h]
    C[select_wrappers.c] --> H
    C --> CM[cmocka.h]
    C --> MOCK[mock()]
    Target[Test target] --> SUT[select-dependent production code]
    Target --> C
    Link[Linker wrapping configuration] --> C
    Socket[wrappers_linux_socket] -. sibling descriptor/socket seam .-> Target
    Pthread[wrappers_posix_pthread] -. sibling synchronization seam .-> Target
    Common[wrappers_common] -. shared test support .-> Target
~~~

Direct dependencies are intentionally small:

- `<sys/select.h>` supplies `fd_set`, `struct timeval`, and the POSIX declarations needed by the prototype.
- `<cmocka.h>` supplies `mock()`.
- `<stddef.h>`, `<stdarg.h>`, and `<setjmp.h>` are included by the implementation as part of its unit-test support environment; the wrapper logic does not directly use their declarations.
- The test build must arrange symbol wrapping so calls intended for the native `select()` resolve to `__wrap_select()`.

There is no dependency on Wazuh DB, queues, configuration files, network services, or the native `select()` implementation at runtime. Tests may combine this wrapper with other seams when the code under test performs socket operations or synchronization; see [wrappers_linux_socket.md](wrappers_linux_socket.md) and [wrappers_posix_pthread.md](wrappers_posix_pthread.md).

## Process flows

### Mocked timeout

~~~mermaid
flowchart TD
    A[Test queues 0] --> B[Caller invokes select]
    B --> C[__wrap_select ignores all arguments]
    C --> D[mock() returns 0]
    D --> E[Caller handles timeout / no readiness]
~~~

### Mocked readiness or error

~~~mermaid
flowchart TD
    A[Test queues positive or negative result] --> B[Caller invokes select]
    B --> C[__wrap_select calls mock()]
    C --> D{Scripted result}
    D -->|positive| E[Caller handles ready-count branch]
    D -->|negative| F[Caller handles error branch]
~~~

The wrapper itself does not distinguish these cases. The distinction is made entirely by the caller based on the integer returned from CMocka.

## Test design guidance

- Queue the expected integer with CMocka before execution reaches `select()`; the wrapper consumes one mocked value per invocation.
- Use `0` to drive timeout/no-ready-descriptor logic and a positive value to drive a readiness-count branch.
- Use a negative value when the caller's error path is being tested. If that path relies on `errno`, configure `errno` explicitly in the test because this wrapper does not set it.
- Do not expect the wrapper to populate or clear `fd_set` values. Set any post-call descriptor state required by the test independently.
- Do not expect `timeout` to be decremented, normalized, or otherwise changed.
- Ensure the wrapper and the code under test are built with compatible POSIX declarations and linker wrapping configuration.
- Because the implementation is excluded under `WIN32`, Windows test targets must use a platform-appropriate seam rather than this module.

## Maintainer notes

The wrapper deliberately models only the return channel of `select()`. Expanding it to mutate descriptor sets or `timeval` would create a broader shared test contract and could make existing tests dependent on simulated readiness details. Such behavior should be introduced only when a concrete test requirement cannot be handled by fixture setup.

The `restrict` qualifiers in the header and implementation preserve the POSIX-compatible function shape. Changes to the declaration should be checked against every test target that links with symbol wrapping, especially targets that combine this seam with socket and event-loop code.

## References

- [POSIX directory wrappers](wrappers_posix_dirent.md)
- [POSIX group wrappers](wrappers_posix_grp.md)
- [POSIX pthread wrappers](wrappers_posix_pthread.md)
- [POSIX password wrappers](wrappers_posix_pwd.md)
- [Linux socket wrappers](wrappers_linux_socket.md)
- [Common test wrappers](wrappers_common.md)
