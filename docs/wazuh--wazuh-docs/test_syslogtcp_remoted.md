# `test_syslogtcp_remoted`

## Introduction

`test_syslogtcp_remoted` is the CMocka unit-test module for the syslog-over-TCP parsing helper used by Wazuh `remoted`. Its scope is deliberately narrow: it verifies `w_get_pri_header_len`, the function that identifies the length of a leading syslog PRI header such as `<18>`.

The test does not open a socket or exercise the complete remoted event loop. It validates the helper’s boundary behavior in isolation, using four representative inputs: a null pointer, a message without a PRI header, a valid PRI header, and an unterminated header-like prefix.

## Module position

The test is part of the **Unit Tests – Remoted** collection and targets the `remoted_syslog_listener` component of the native remoted daemon.

```mermaid
graph TB
    SUITE[Unit Tests - Remoted]
    TEST[test_syslogtcp_remoted\nsrc/unit_tests/remoted/test_syslogtcp.c]
    PROD[src/remoted/syslogtcp.c\nw_get_pri_header_len]
    REMOTED[src/remoted/remoted.c and remoted.h\nremoted daemon context]
    SYSLOG[src/remoted/syslog.c\nsyslog listener]
    NET[src/os_net/os_net.c\nnetwork primitives]
    CFG[src/config/remote-config.h\nremoted configuration]

    SUITE --> TEST
    TEST --> PROD
    TEST -. includes .-> REMOTED
    TEST -. includes .-> NET
    SYSLOG --> PROD
    REMOTED --> SYSLOG
    CFG --> SYSLOG
```

### Related documentation

| Reference | Relationship |
|---|---|
| [remoted_syslog_listener.md](remoted_syslog_listener.md) | Production syslog listener responsibilities and its place in remoted networking. |
| [remoted.md](remoted.md) | Overall native `remoted` daemon lifecycle and subsystem relationships. |
| [Remote_Config.md](Remote_Config.md) | Configuration structures that control remote listeners and protocols. |
| [shared_lib_networking.md](shared_lib_networking.md) | Shared networking primitives used by remoted. |
| [test_infrastructure.md](test_infrastructure.md) | Common unit-test conventions, wrappers, and CMocka infrastructure. |

## Architecture and dependencies

The test has one production behavior under test and two header-level dependencies. `remoted.h` and `shared.h` provide shared declarations/types, while `os_net.h` supplies the networking context included by the test translation unit. The test itself does not define or mock network operations because `w_get_pri_header_len` is a pure string-inspection helper.

```mermaid
graph LR
    T[test_syslogtcp.c]
    CMOCKA[CMocka\nCMUnitTest / assertions / runner]
    H1[remoted/remoted.h]
    H2[headers/shared.h]
    H3[os_net/os_net.h]
    I[src/remoted/syslogtcp.c]
    G[test_mode global]

    T --> CMOCKA
    T --> H1
    T --> H2
    T --> H3
    T --> I
    group_setup --> G
    group_teardown --> G
```

The dependency boundary is intentionally small:

| Dependency | Role in this module |
|---|---|
| `cmocka.h` | Supplies `CMUnitTest`, `cmocka_unit_test`, group execution, and assertions. |
| `../../remoted/remoted.h` | Remoted declarations and shared daemon context included by the test. |
| `../../headers/shared.h` | Common Wazuh declarations included by the test. |
| `../../os_net/os_net.h` | Shared network declarations included by the test. |
| `w_get_pri_header_len` | Production helper declared locally with a forward declaration and linked from `syslogtcp.c`. |

## Test harness lifecycle

The group setup and teardown functions manage only the global test-mode flag. They do not allocate sockets, initialize a listener, or construct a syslog message object.

```mermaid
flowchart TD
    START[main] --> REGISTER[Create four CMUnitTest entries]
    REGISTER --> RUN[cmocka_run_group_tests]
    RUN --> SETUP[group_setup]
    SETUP --> MODE1[test_mode = 1]
    MODE1 --> CASES[Run test cases]
    CASES --> TEARDOWN[group_teardown]
    TEARDOWN --> MODE0[test_mode = 0]
    MODE0 --> EXIT[Return CMocka result]
```

`state` is accepted by the CMocka callbacks but is not used. This makes the fixture suitable for a stateless helper test while preserving the standard group-test interface used throughout the remoted unit-test suite.

## Component interaction

Each test calls the same helper directly and compares its return value with an expected header length. No wrapper calls or external side effects are expected.

```mermaid
sequenceDiagram
    participant C as CMocka runner
    participant F as test_w_get_pri_header_len_*
    participant H as w_get_pri_header_len
    participant A as Assertion

    C->>F: invoke test case
    F->>H: pass one input string
    H-->>F: return header length
    F->>A: compare actual with expected
    A-->>C: pass or fail
```

The production helper is expected to inspect only the beginning of the supplied string:

1. A null pointer is invalid and produces length `0`.
2. A normal message without `<...>` at offset zero produces length `0`.
3. A complete PRI header includes the opening bracket, numeric value, and closing bracket. For `<18>test log`, the length is `4`.
4. A prefix without the closing bracket is not a valid PRI header. For `<18 test log`, the length is `0`.

## Data flow and parsing contract

```mermaid
flowchart LR
    INPUT[syslog message text] --> NULL{message is NULL?}
    NULL -->|yes| ZERO[return 0]
    NULL -->|no| PREFIX{starts with < and has a closed PRI prefix?}
    PREFIX -->|no| ZERO2[return 0]
    PREFIX -->|yes| COUNT[count bytes through >]
    COUNT --> RESULT[return PRI header length]
```

The helper’s output is a length, not the parsed priority value. The tests therefore establish a framing/offset contract for callers: a caller can use a nonzero result to identify the number of leading bytes occupied by the PRI header, while a zero result means that no complete leading PRI header was recognized.

The test does not specify whether a broader syslog parser subsequently validates the numeric range or parses the remaining message body. Those responsibilities belong to the production syslog listener and are covered by [remoted_syslog_listener.md](remoted_syslog_listener.md).

## Test inventory

```mermaid
graph TD
    MAIN[main]
    MAIN --> N[test_w_get_pri_header_len_null\nexpected 0]
    MAIN --> NP[test_w_get_pri_header_len_no_pri\nexpected 0]
    MAIN --> P[test_w_get_pri_header_len_w_pri\nexpected 4]
    MAIN --> E[test_w_get_pri_header_len_not_end\nexpected 0]
```

| Test | Input | Expected return | Contract |
|---|---|---:|---|
| `test_w_get_pri_header_len_null` | `NULL` | `0` | Safely handles a null message pointer. |
| `test_w_get_pri_header_len_no_pri` | `test log` | `0` | Does not treat ordinary text as a PRI header. |
| `test_w_get_pri_header_len_w_pri` | `<18>test log` | `4` | Recognizes and counts a complete leading PRI header. |
| `test_w_get_pri_header_len_not_end` | `<18 test log` | `0` | Rejects an incomplete/unterminated PRI prefix. |

## Process flow and failure interpretation

```mermaid
flowchart TD
    INVOKE[Invoke helper with fixture input] --> RET[Capture ssize_t return value]
    RET --> ASSERT{equals expected value?}
    ASSERT -->|yes| PASS[case passes]
    ASSERT -->|no| FAIL[case fails and reports regression]
    PASS --> NEXT{more cases?}
    NEXT -->|yes| INVOKE
    NEXT -->|no| SUMMARY[CMocka group summary]
    FAIL --> SUMMARY
```

A failure usually indicates one of these regressions:

- null input is dereferenced or classified as a valid header;
- ordinary messages are incorrectly treated as PRI-prefixed;
- the returned length excludes or includes the wrong delimiter bytes;
- an incomplete `<PRI`-style prefix is accepted;
- the test registration or group runner no longer executes all four cases.

## Maintenance guidance

When changing `w_get_pri_header_len`, preserve the distinction between a complete header and a header-like prefix. Add focused cases here if the accepted grammar changes, such as additional delimiter rules or numeric-format rules. Keep broader socket, framing, listener, and configuration behavior in the production documentation referenced above rather than duplicating it in this unit-test document.

The test is self-contained and should not require a live TCP endpoint, an initialized remoted daemon, an agent, or external configuration. Its only mutable shared state is `test_mode`, which must be restored by `group_teardown` so later remoted tests are not affected.
