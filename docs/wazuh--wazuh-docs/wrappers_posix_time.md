# wrappers_posix_time

## Introduction

`wrappers_posix_time` is Wazuh unit-test infrastructure for replacing selected POSIX time APIs with deterministic CMocka-controlled test doubles. It intercepts calls to `time()`, `ctime_r()`, and `gettimeofday()` so tests can control timestamps, verify `ctime_r()` inputs, and inject `struct timeval` values without depending on wall-clock time.

The module is test-only. It has no production scheduling behavior, persistent state, clock management, or interaction with the operating-system clock once a call has been redirected. It is part of the broader wrapper and mock infrastructure documented in [test_infrastructure.md](test_infrastructure.md), and can be combined with related POSIX seams such as [wrappers_posix_select.md](wrappers_posix_select.md), [wrappers_posix_pthread.md](wrappers_posix_pthread.md), and [wrappers_posix_stat.md](wrappers_posix_stat.md).

## Scope and responsibilities

| Component | Location | Responsibility |
|---|---|---|
| Time wrapper implementation | `src/unit_tests/wrappers/posix/time_wrappers.c` | Implements the wrapped time functions and delegates test-controlled behavior to CMocka. |
| Wrapper interface | `src/unit_tests/wrappers/posix/time_wrappers.h` | Imports POSIX time types and exposes the wrapper prototypes. |
| `timeval` | `struct timeval` from `<sys/time.h>` | Carries seconds and microseconds injected into `gettimeofday()`. |
| CMocka mock state | `<cmocka.h>` | Supplies return values, pointers, and expected arguments. |

The implementation also contains `__wrap_ctime_r`, although the module tree identifies the primary components as `__wrap_time`, `__wrap_gettimeofday`, and `timeval`. `ctime_r()` is documented here because it is part of the compiled wrapper source and its behavior is relevant to maintainers.

## Architecture

~~~mermaid
flowchart LR
    Test[Test case] -->|configures values and expectations| CM[CMocka state]
    Test --> UUT[Code under test]
    UUT -->|wrapped time API call| W[time_wrappers.c]
    W -->|mock_type / mock_ptr_type| CM
    W -->|returns or copies controlled data| UUT
    H[time_wrappers.h] --> T[POSIX time.h and sys/time.h]
    W --> H
    Build[Test linker configuration] -->|redirects symbols| W
    W -. never uses .-> Clock[Real operating-system clock]
~~~

The wrapper preserves the callable shape expected by the system under test while replacing external time sources with test data. Each function controls a different part of the API contract:

- `__wrap_time()` controls the returned epoch value.
- `__wrap_ctime_r()` controls the formatted string and checks the input `time_t` pointer.
- `__wrap_gettimeofday()` controls the output `struct timeval` copied into the caller's buffer.

## Public interface

The header declares the following test symbols:

~~~c
time_t __wrap_time(time_t *t);
char *__wrap_ctime_r(const time_t *timep, char *buf);
void __wrap_gettimeofday(struct timeval *__restrict tv,
                         void *__restrict tz);
~~~

The declarations depend on:

- `<time.h>` for `time_t` and the time-related API types.
- `<sys/time.h>` for `struct timeval` and the `gettimeofday()` contract.

The `__wrap_` prefix is intended for linker-level symbol wrapping. The production code continues to call the normal POSIX symbol; the test executable redirects that symbol to the corresponding wrapper.

## Core components

### `__wrap_time`

~~~c
time_t __wrap_time(__attribute__((unused)) time_t *t) {
    return mock_type(time_t);
}
~~~

This function ignores the optional output pointer and returns the next CMocka value of type `time_t`.

Behavioral contract:

| Condition | Result |
|---|---|
| A `time_t` value is configured in CMocka | That value is returned. |
| The caller passes a non-null `t` | The pointer is not written to by this wrapper. |
| No value is configured | Behavior follows the active CMocka configuration; tests should configure one explicitly. |

Unlike the native `time()` function, this wrapper does not obtain the current time and does not populate `*t`. Tests that inspect the output pointer must model that state separately or use a test-specific fixture.

### `__wrap_ctime_r`

~~~c
char *__wrap_ctime_r(const time_t *timep, char *buf) {
    check_expected(timep);
    strncpy(buf, mock_type(const char *), 26);
    return buf;
}
~~~

The wrapper validates the `timep` argument with CMocka, copies a mocked string into `buf`, and returns `buf`, matching the normal `ctime_r()` return convention.

Important details:

- The expected argument is the `time_t` pointer itself, not the pointed-to timestamp.
- The copy requests at most 26 characters through `strncpy`.
- The source string must be configured by the test and should be suitable for the destination buffer.
- The wrapper does not call the real `ctime_r()` and therefore does not format a timestamp itself.
- As with the native `strncpy` contract, callers and tests must account for termination behavior when the mocked source is 26 characters or longer.

### `__wrap_gettimeofday`

~~~c
void __wrap_gettimeofday(struct timeval *__restrict tv,
                         __attribute__((unused)) void *__restrict tz) {
    struct timeval *mocked_time = mock_ptr_type(struct timeval *);
    if (mocked_time && tv) {
        *tv = *mocked_time;
    }
}
~~~

This function obtains a pointer to a test-provided `struct timeval`. If both the mocked pointer and the caller's `tv` pointer are non-null, it copies the complete structure into `*tv`.

The `tz` argument is accepted for API compatibility and ignored. A null mocked pointer or null destination results in no write and no explicit error return because the wrapper has a `void` return type.

### `timeval`

`timeval` is not a replacement structure defined by this module. It refers to the POSIX `struct timeval` imported from `<sys/time.h>`. Its fields are supplied by the platform header and are copied as a complete value by `__wrap_gettimeofday()`.

## Data flow and component interaction

~~~mermaid
sequenceDiagram
    participant F as Test fixture
    participant C as CMocka
    participant P as Code under test
    participant W as POSIX time wrapper

    F->>C: Configure time_t, string, or timeval pointer
    F->>P: Run time-dependent operation
    P->>W: Invoke wrapped POSIX API
    alt time()
        W->>C: mock_type(time_t)
        C-->>W: Scripted epoch value
        W-->>P: Return epoch value
    else ctime_r()
        W->>C: check_expected(timep)
        W->>C: mock_type(const char *)
        W-->>P: Copy string and return buf
    else gettimeofday()
        W->>C: mock_ptr_type(struct timeval *)
        C-->>W: Scripted timeval pointer
        W-->>P: Copy timeval when pointers are valid
    end
~~~

The wrapper is an injection seam rather than a full clock simulator. It controls only the values explicitly implemented in the source; it does not advance time, maintain a monotonic timeline, or coordinate values between successive API calls.

## Dependency relationships

~~~mermaid
graph TD
    H[time_wrappers.h] --> TIME[time.h]
    H --> STIME[sys/time.h]
    C[time_wrappers.c] --> H
    C --> CM[cmocka.h]
    C --> STR[string.h]
    C --> MOCK[mock_type / mock_ptr_type]
    C --> EXPECT[check_expected]
    Target[Test executable] -->|linker symbol wrapping| C
    Target --> UUT[Time-dependent unit under test]
    Select[wrappers_posix_select] -. sibling timing/event seam .-> Target
    Pthread[wrappers_posix_pthread] -. sibling synchronization seam .-> Target
    Common[wrappers_common] -. shared test support .-> Target
~~~

Direct implementation dependencies are intentionally narrow:

- `time_wrappers.h` supplies the POSIX declarations and wrapper prototypes.
- CMocka supplies `mock_type`, `mock_ptr_type`, and `check_expected`.
- `<string.h>` supplies `strncpy` for the `ctime_r()` test double.
- The test build supplies linker wrapping or an equivalent symbol-substitution mechanism.

There is no runtime dependency on Wazuh databases, queues, configuration files, network services, or the real clock implementation.

## Process flows

### Injecting a deterministic epoch value

~~~mermaid
flowchart TD
    A[Test configures time_t return value] --> B[Code under test calls time]
    B --> C[Linker redirects call to __wrap_time]
    C --> D[mock_type(time_t)]
    D --> E[Wrapper returns scripted timestamp]
    E --> F[Caller executes deterministic time-dependent branch]
~~~

### Injecting wall-clock fields

~~~mermaid
flowchart TD
    A[Test creates struct timeval] --> B[Test configures mocked pointer]
    B --> C[Code calls gettimeofday]
    C --> D[__wrap_gettimeofday reads mock pointer]
    D --> E{mocked pointer and tv non-null?}
    E -->|Yes| F[Copy seconds and microseconds]
    E -->|No| G[Do not write destination]
    F --> H[Caller continues]
    G --> H
~~~

### Formatting a controlled timestamp

~~~mermaid
flowchart TD
    A[Test configures expected timep and string] --> B[Code calls ctime_r]
    B --> C[__wrap_ctime_r checks timep]
    C --> D{Expectation passes?}
    D -->|No| E[CMocka fails the test]
    D -->|Yes| F[Copy up to 26 characters into buf]
    F --> G[Return buf to caller]
~~~

## Test design guidance

- Configure a `time_t` mock before code reaches `time()`; the wrapper consumes a CMocka value for each invocation.
- Do not assume `__wrap_time()` writes through its argument. If the system under test depends on that native side effect, initialize the output state explicitly in the fixture or extend the seam only for a demonstrated requirement.
- For `ctime_r()`, register an expectation for the `timep` pointer and provide a mocked string. Ensure the destination buffer is large enough for the intended copy.
- For `gettimeofday()`, provide a valid `struct timeval` pointer when the caller is expected to receive data. Test null-pointer behavior separately if relevant.
- The timezone argument is ignored; tests should not expect timezone conversion or mutation.
- These wrappers do not model monotonic time, elapsed time, clock progression, or `errno`. Tests for those behaviors should control the relevant state independently.
- Keep this module side-effect free and deterministic. It should never call the real time functions.
- Because the interface is POSIX-specific, use a platform-appropriate wrapper on non-POSIX targets rather than assuming this module is available everywhere.

## Maintenance notes

The implementation includes standard CMocka support headers (`stdarg.h`, `stddef.h`, `setjmp.h`) as part of the unit-test wrapper environment. The observable behavior is defined by the three wrapped APIs and should remain stable for existing test targets.

Any signature change must be applied consistently to `time_wrappers.h`, `time_wrappers.c`, and the relevant test build/linker configuration. In particular, preserve the `struct timeval` and `restrict`-qualified interface expected by POSIX callers.

If richer clock semantics are added, document whether values are independent per call or driven by a shared simulated clock. That distinction affects tests that combine `time()`, `ctime_r()`, and `gettimeofday()` in one execution path.

## References

- [Test infrastructure](test_infrastructure.md)
- [POSIX select wrappers](wrappers_posix_select.md)
- [POSIX pthread wrappers](wrappers_posix_pthread.md)
- [POSIX stat wrappers](wrappers_posix_stat.md)
- [POSIX signal wrappers](wrappers_posix_signal.md)
- [POSIX directory wrappers](wrappers_posix_dirent.md)
- [Common test wrappers](wrappers_common.md)
