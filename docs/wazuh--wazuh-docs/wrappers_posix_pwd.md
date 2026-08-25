# wrappers_posix_pwd

## Introduction

wrappers_posix_pwd is Wazuh unit-test infrastructure for controlling POSIX password-database lookups. It replaces selected functions from pwd.h with deterministic wrappers so tests can exercise account-resolution code without reading /etc/passwd, consulting NSS, or depending on host identity services.

This is a test seam, not production functionality. It has no daemon lifecycle, persistent state, database, or standalone executable. Its sibling group-account seam is documented in [wrappers_posix_grp.md](wrappers_posix_grp.md).

## Scope and responsibilities

| Component | Location | Responsibility |
|---|---|---|
| Password wrapper implementation | src/unit_tests/wrappers/posix/pwd_wrappers.c | Implements wrapped getpwnam_r and getpwuid_r behavior. |
| Wrapper interface | src/unit_tests/wrappers/posix/pwd_wrappers.h | Includes POSIX password types and declares platform-dependent wrapper signatures. |
| Password record model | pwd.h | Supplies struct passwd and uid_t. |
| Mock control | cmocka.h | Supplies mock_type() and mock() for scripted UID lookup behavior. |

Both source files are guarded by #ifndef WIN32. On Windows, the declarations and implementations are omitted because this module targets Unix-like test builds.

## Architecture

~~~mermaid
flowchart LR
    Test[Test case / fixture] -->|queues mock values| CMocka[CMocka mock state]
    Test --> SUT[Code under test]
    SUT -->|wrapped POSIX symbol| W[pwd_wrappers.c]
    W -->|struct passwd / uid_t| POSIX[pwd.h]
    W -->|deterministic result| SUT
    W -.-> CMocka
    Build[Test linker / wrapping flags] -->|redirects calls| W
~~~

The wrapper isolates account-dependent code from the operating system. Name lookups use a fixed deterministic model, while UID lookups obtain their result from CMocka so tests can represent success, absence, or an error without changing the system database.

## Public interface

### __wrap_getpwnam_r

~~~c
int __wrap_getpwnam_r(const char *name,
                      struct passwd *pwd,
                      char *buf,
                      size_t buflen,
                      struct passwd **result);
~~~

The signature mirrors the usual POSIX reentrant name lookup. The implementation accepts the caller’s struct passwd, scratch buffer, buffer length, and result pointer, but only uses name, pwd, buflen, and result; the buffer itself is not read or written.

### __wrap_getpwuid_r on non-Solaris systems

~~~c
int __wrap_getpwuid_r(uid_t uid,
                      struct passwd *pwd,
                      char *buf,
                      size_t buflen,
                      struct passwd **result);
~~~

The uid, buf, and buflen arguments are intentionally unused. The wrapper obtains pwd->pw_name, *result, and the function return code from CMocka.

### __wrap_getpwuid_r on Solaris

~~~c
struct passwd **__wrap_getpwuid_r(uid_t uid,
                                  struct passwd *pwd,
                                  char *buf,
                                  size_t buflen);
~~~

When SOLARIS is defined, the platform ABI exposed by the header has a pointer-to-pointer return value and no result argument. The implementation obtains pwd->pw_name and the returned struct passwd ** from CMocka. This conditional signature matches the Solaris getpwuid_r interface.

### passwd

The module-tree passwd component is the native struct passwd type imported from pwd.h. The wrapper does not define or replace the structure. Fixtures own any record and string storage they provide.

## Implementation behavior

### Name lookup: __wrap_getpwnam_r

The implementation follows this sequence:

1. Set *result = NULL.
2. If buflen is less than 1024, return ERANGE immediately.
3. If name is exactly "wazuh", assign pwd->pw_uid = 1000 and set *result = pwd.
4. Return 0.

For an unknown name and a sufficiently large buffer, the return value is 0 while *result remains NULL. Matching is exact and case-sensitive.

Only pw_uid is populated for the synthetic account. The wrapper does not initialize pw_name, pw_passwd, pw_gid, pw_gecos, pw_dir, pw_shell, or platform-specific fields. Tests whose callers inspect those fields must initialize them explicitly.

The function does not call the real getpwnam_r, update errno, allocate memory, or copy data into buf.

### UID lookup: __wrap_getpwuid_r

UID lookup is entirely CMocka-driven. On non-Solaris systems, each call performs the equivalent of:

~~~c
pwd->pw_name = mock_type(char*);
*result = mock_type(struct passwd*);
return mock();
~~~

The requested UID is ignored. The fixture controls the returned name pointer, result pointer, and integer status independently.

On Solaris, the wrapper performs the first two assignments but returns mock_type(struct passwd*) as a pointer-to-pointer result, matching the Solaris declaration. The Solaris form does not call mock() for an integer status.

Because the wrapper returns pointers supplied by the fixture, it performs no allocation, duplication, ownership transfer, or cleanup.

## Data flow and component interaction

~~~mermaid
sequenceDiagram
    participant F as Test fixture
    participant P as Code under test
    participant W as Password wrapper
    participant M as CMocka
    alt Name lookup
        P->>W: __wrap_getpwnam_r(name, pwd, buf, buflen, result)
        W->>W: Set *result = NULL
        alt buflen < 1024
            W-->>P: ERANGE
        else name == "wazuh"
            W->>W: pwd->pw_uid = 1000
            W->>W: *result = pwd
            W-->>P: 0 and synthetic record
        else Other name
            W-->>P: 0 and NULL result
        end
    else UID lookup
        F->>M: Queue name, result, and status values
        P->>W: __wrap_getpwuid_r(uid, pwd, buf, buflen[, result])
        W->>M: mock_type / mock
        M-->>W: Scripted values
        W-->>P: Pointer and/or status
    end
~~~

The name path is independent of the CMocka queue. The UID path consumes values configured by the test, so setup order matters when multiple mocked calls occur.

## Dependency relationships

~~~mermaid
graph TD
    H[pwd_wrappers.h] --> PWD[pwd.h]
    H --> STD[stddef.h]
    C[pwd_wrappers.c] --> H
    C --> ERR[errno.h]
    C --> STR[string.h]
    C --> CM[cmocka.h]
    C --> TYPE[struct passwd / uid_t]
    Target[Test target] --> C
    Target --> SUT[Password-dependent production code]
    Build[Linker symbol wrapping] --> C
    Grp[wrappers_posix_grp] -. sibling group lookup seam .-> Target
    Stat[wrappers_posix_stat] -. sibling filesystem seam .-> Target
~~~

Direct dependencies are intentionally limited:

- pwd.h provides struct passwd and uid_t.
- stddef.h provides size_t.
- errno.h provides ERANGE.
- string.h provides the exact strcmp used for the synthetic name.
- CMocka provides mock_type() and mock().
- The test build supplies symbol redirection from production calls to __wrap_*; the header only declares functions and does not define aliases.

There is no runtime dependency on Wazuh DB, sockets, cluster services, configuration files, or the real password database. Consumers may combine this seam with POSIX group, stat, unistd, or pthread wrappers when a test exercises several OS boundaries.

## Process flows

### Synthetic Wazuh account lookup

~~~mermaid
flowchart TD
    A[Caller prepares passwd and result] --> B[Call __wrap_getpwnam_r("wazuh", ...)]
    B --> C{buflen >= 1024?}
    C -->|no| D[Set result NULL; return ERANGE]
    C -->|yes| E[Set pw_uid to 1000]
    E --> F[Set result to pwd]
    F --> G[Return 0]
~~~

### Unknown account lookup

~~~mermaid
flowchart TD
    A[Caller supplies another name] --> B[Set result NULL]
    B --> C{buflen >= 1024?}
    C -->|no| D[Return ERANGE]
    C -->|yes| E[Return 0 with no match]
~~~

### Mocked UID lookup

~~~mermaid
flowchart TD
    A[Test queues char* and passwd* values] --> B[Caller invokes __wrap_getpwuid_r]
    B --> C[Assign pwd->pw_name from mock_type(char*)]
    C --> D[Assign result pointer from mock_type(struct passwd*)]
    D --> E{Platform ABI}
    E -->|non-Solaris| F[Return mock() status]
    E -->|Solaris| G[Return mocked struct passwd**]
    F --> H[Caller exercises success / absence / error path]
    G --> H
~~~

## Test design guidance

- Use a buffer length below 1024 to exercise the deterministic ERANGE branch of __wrap_getpwnam_r.
- Use the exact lowercase name "wazuh" to receive the synthetic UID 1000; this value is a test fixture, not a platform guarantee.
- For unknown names with a buffer of at least 1024 bytes, assert both return code 0 and *result == NULL.
- Initialize every struct passwd field that the system under test reads. The name wrapper only fills pw_uid; the UID wrapper only assigns pw_name and the result pointer from mocks.
- Queue typed CMocka values before invoking code that reaches __wrap_getpwuid_r. Include a char *, a struct passwd *, and, on non-Solaris builds, a compatible integer return value.
- Keep fixture-backed strings and records alive for the full call chain. The wrapper returns pointers directly and does not copy or free them.
- Do not expect native NSS behavior, errno updates, buffer writes, allocation, or cleanup.
- Compile the relevant test target with the same SOLARIS condition used by the production ABI. A mismatch between the wrapper declaration and the linked call convention can cause compilation or runtime failures.

## Maintainer notes

The "wazuh"/1000 mapping is deliberately synthetic. It must not be interpreted as the deployed Wazuh service account UID, which is environment-dependent.

The SOLARIS branch is an ABI compatibility point rather than a behavioral variant: it changes the declaration and return shape of getpwuid_r. Any change to that branch should be checked against all Solaris test targets and platform headers.

The wrapper intentionally leaves most struct passwd fields untouched. Expanding the synthetic record may simplify individual tests but also changes the shared test contract; prefer fixture initialization when only one consumer needs additional fields.

## References

- [POSIX group wrappers](wrappers_posix_grp.md)
- [POSIX directory wrappers](wrappers_posix_dirent.md)
- [POSIX pthread wrappers](wrappers_posix_pthread.md)
- [POSIX time wrappers](wrappers_posix_time.md)
- [Data provider Unix wrappers](data_provider_wrappers_unix.md)
- [Data provider Linux groups](data_provider_groups_linux.md)
