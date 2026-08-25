# test_audit_op_shared

## Introduction

test_audit_op_shared is the CMocka unit-test module for Wazuh's shared Linux Audit helpers. Its source is src/unit_tests/shared/test_audit_op.c. It validates Audit rule creation, deletion, discovery, parsing, caching, path normalization, and auditd restart handling without requiring a live kernel Audit subsystem, root privileges, or a running service.

Production semantics are documented in [shared_lib_system_utils_audit.md](shared_lib_system_utils_audit.md). This document focuses on the test harness and its contracts; the module belongs to [Unit_Tests_-_Shared_Library.md](Unit_Tests_-_Shared_Library.md).

## Module position

~~~mermaid
graph TB
    SUITE[Unit Tests - Shared Library] --> TEST[test_audit_op_shared]
    TEST --> PROD[src/shared/audit_op.c]
    TEST --> HDR[src/headers/audit_op.h]
    TEST -. mocked .-> LIBAUDIT[libaudit wrappers]
    TEST -. mocked .-> OS[libc / select / exec / logging wrappers]
    CALLER[syscheckd_whodata] --> PROD
~~~

The test calls production functions directly while replacing operating-system and libaudit boundaries with CMocka wrappers.

## Harness architecture

~~~mermaid
flowchart LR
    MAIN[main] --> REGISTER[CMUnitTest table]
    REGISTER --> RUN[cmocka_run_group_tests]
    RUN --> SETUP[group_setup]
    SETUP --> CASE[test case]
    CASE --> EXPECT[expect_value / will_return]
    EXPECT --> SUT[audit_op.c]
    SUT --> MOCK[wrapped external calls]
    SUT --> CACHE[audit_rules_list]
    CASE --> ASSERT[return, state, log assertions]
    ASSERT --> CLEAN[group or fixture teardown]
~~~

### Lifecycle and fixtures

group_setup sets Wazuh test_mode = 1; group_teardown resets it and calls audit_rules_list_free(). This prevents the global rule cache from leaking between cases.

| Fixture | Purpose |
|---|---|
| test_setup_kernel_get_reply / teardown | Allocates three synthetic audit_reply objects: successful NLMSG_ERROR, an AUDIT_LIST_RULES rule reply, and a terminal reply. |
| test_setup_print_reply / teardown | Creates a rule reply containing directory, filter-key, and full rwxa permissions. |
| test_setup_file / teardown | Allocates a zeroed wfd_t for audit_restart; tests provide a synthetic output stream. |
| test_teardown_free_path | Frees the heap string returned by audit_clean_path. |

## Dependencies and mocked boundaries

~~~mermaid
graph LR
    TEST[test_audit_op_shared] -->|links/calls| AUDITOP[audit_op.c]
    TEST -->|types and constants| HEADER[audit_op.h / defs.h / exec_op.h / list_op.h]
    TEST --> CMOCKA[cmocka]
    AUDITOP -->|wrapped| A[libaudit]
    AUDITOP -->|wrapped| B[select and errno]
    AUDITOP -->|wrapped| C[wpopenv / wpclose / fgets]
    AUDITOP -->|wrapped| D[get_binary_path / stat]
    AUDITOP -->|wrapped| E[mdebug1 / mdebug2 / merror]
    AUDITOP -->|real in-memory state| LIST[OSList of w_audit_rule]
~~~

The test includes external Audit wrappers when not building TEST_WINAGENT, plus wrappers for standard I/O, POSIX polling, Wazuh logging, executable lookup, and process execution. The wrappers make call order, arguments, return values, and diagnostics observable.

## Data model

~~~mermaid
classDiagram
    class audit_replies {
        +audit_reply* reply1
        +audit_reply* reply2
        +audit_reply* reply3
    }
    class audit_reply {
        +int type
        +nlmsgerr* error
        +audit_rule_data* ruledata
    }
    class w_audit_rule {
        +char* path
        +char* key
        +int perm
    }
    class OSList {
        +first_node
        +currently_size
    }
    audit_replies --> audit_reply
    OSList "1" o-- "many" w_audit_rule
~~~

The production list is intentionally real rather than mocked. Tests therefore verify observable cache state: initialization, node presence, size, extracted path/key, and permission mask.

## Functional flows

### Rule listing and kernel replies

~~~mermaid
sequenceDiagram
    participant T as Test
    participant F as audit_get_rule_list
    participant K as wrapped libaudit
    participant L as audit_rules_list
    T->>F: fd 0
    F->>K: audit_send(AUDIT_LIST_RULES)
    K-->>F: success
    loop bounded polling
        F->>K: select(100 ms)
        F->>K: audit_get_reply(NONBLOCKING)
        K-->>F: reply / no reply
        F->>L: audit_print_reply and append
    end
    F-->>T: 1 and populated cache
~~~

test_audit_get_rule_list checks the successful request and non-null cache. test_audit_get_rule_list_error makes audit_send return -1, expects the formatted error, and checks -1. test_kernel_get_reply covers an interrupted/failed select followed by synthetic success and terminal replies.

### Reply parsing and searching

~~~mermaid
flowchart TD
    R[Audit list reply] --> P[audit_print_reply]
    P --> X[extract path, key, permissions]
    X --> A[audit_rules_list_append]
    A --> C[audit_rules_list]
    C --> S[search_audit_rule]
    S -->|match| FOUND[1]
    S -->|valid no match| NONE[0]
    S -->|NULL path/key| BAD[-1]
~~~

test_audit_print_reply expects the debug message Audit rule loaded: -w  -p rwxa -k , then verifies one cached rule with empty path/key and all four permission bits. test_audit_rules_list_append appends 30 rules and checks the resulting size of 31. The search tests cover found, not-found, and null-argument outcomes.

### Add/delete rule management

~~~mermaid
sequenceDiagram
    participant T as Test
    participant M as audit_manage_rules
    participant K as wrapped libaudit
    T->>M: audit_add_rule / audit_delete_rule
    M->>K: audit_open
    M->>K: audit_add_watch_dir(AUDIT_DIR, path)
    M->>K: audit_update_watch_perms(WRITE|ATTR)
    M->>K: audit_rule_fieldpair_data(key=bin-folder)
    alt add
        M->>K: audit_add_rule_data
    else delete
        M->>K: audit_delete_rule_data
        K-->>M: -1 and translated error
    end
    M->>K: audit_close
    M-->>T: success or -1
~~~

test_audit_add_rule verifies the complete happy path for /usr/bin, AUDIT_PERM_WRITE | AUDIT_PERM_ATTR, and bin-folder. test_audit_delete_rule verifies the delete path and error translation.

The management failure tests cover Audit open failure, missing-path stat, watch creation failure, permission update failure, overlong key rejection, field-pair encoding failure, and invalid action. They assert -1 and, where relevant, exact diagnostics and cleanup.

### Path normalization

~~~mermaid
flowchart LR
    INPUT[cwd=/home/folder; path=../test/file] --> CLEAN[audit_clean_path]
    CLEAN --> OUTPUT[/home/test/file]
    OUTPUT --> ASSERT[test_audit_clean_path]
~~~

The teardown frees the returned string, documenting that callers own the normalized path.

### Restarting auditd

~~~mermaid
flowchart TD
    START[audit_restart] --> LOOKUP[get_binary_path(service)]
    LOOKUP --> SPAWN[wpopenv]
    SPAWN -->|NULL| OPENERR[-1 and error log]
    SPAWN -->|wfd| READ[fgets output]
    READ --> LOG[mdebug1 auditd line]
    LOG --> CLOSE[wpclose]
    CLOSE --> STATUS{exit status}
    STATUS -->|0| OK[0]
    STATUS -->|127| EXE[-1 launch error]
    STATUS -->|other nonzero| SERVICE[-1 restart error]
~~~

test_audit_restart verifies lookup, process creation, output forwarding, EOF, and successful close. The open-error, exec-error, and service-error tests verify distinct failure logs and return -1.

## Test inventory

~~~mermaid
graph TD
    MAIN[main] --> LIST[listing and replies]
    MAIN --> CACHE[cache and search]
    MAIN --> PATH[path cleanup]
    MAIN --> RESTART[auditd restart]
    MAIN --> MUTATE[add, delete, management errors]
~~~

| Area | Tests |
|---|---|
| Listing | test_audit_get_rule_list_error, test_audit_get_rule_list, test_kernel_get_reply |
| Parsing/cache | test_audit_print_reply, test_audit_rules_list_append |
| Search | test_search_audit_rule, test_search_audit_rule_not_found, test_search_audit_rule_null |
| Paths | test_audit_clean_path |
| Restart | test_audit_restart, test_audit_restart_open_error, test_audit_restart_close_exec_error, test_audit_restart_close_error |
| Mutation | test_audit_add_rule, test_audit_delete_rule |
| Mutation failures | test_audit_manage_rules_open_error, test_audit_manage_rules_stat_error, test_audit_manage_rules_add_dir_error, test_audit_manage_rules_update_perms_error, test_audit_manage_rules_key_length_error, test_audit_manage_rules_fieldpair_error, test_audit_manage_rules_action_error |

main registers these cases with CMocka setup/teardown variants and runs them as one group. Group teardown is required because several cases mutate the global cache.

## Relationship to production consumers

~~~mermaid
graph TB
    TEST[test_audit_op_shared] -->|verifies low-level contract| AUDIT[shared_lib_system_utils_audit]
    AUDIT --> WHODATA[syscheckd_whodata]
    WHODATA --> RULES[audit_rule_handling]
    WHODATA --> HEALTH[audit_healthcheck]
    RULES -->|add/delete/search| AUDIT
    HEALTH -->|list/restart/path normalization| AUDIT
~~~

The test does not duplicate Syscheck's reconciliation and health-check behavior. Those integration responsibilities are described in [syscheckd_whodata_audit.md](syscheckd_whodata_audit.md), while the low-level production API is described in [shared_lib_system_utils_audit.md](shared_lib_system_utils_audit.md).

## Verification strategy and limitations

The harness deterministically covers call ordering, arguments, return-code propagation, error logging, bounded polling, kernel-reply parsing, cache lifecycle, search semantics, process exit handling, and fixture cleanup.

It does not verify real Linux Netlink behavior, actual rule installation, a real service manager, concurrent cache mutation, end-to-end Audit event delivery, or builds where ENABLE_AUDIT is disabled. Those concerns belong to integration/system tests and Syscheck's whodata tests.

Wrapper details are maintained in [Unit_Test_Wrappers_%26_Mocks.md](Unit_Test_Wrappers_%26_Mocks.md); the underlying OSList implementation is covered by [shared_lib_data_structures.md](shared_lib_data_structures.md).

## Maintenance guidance

When changing src/shared/audit_op.c, update expectations for altered calls or cleanup, add focused tests for new error branches, preserve cache cleanup, and keep production semantics in [shared_lib_system_utils_audit.md](shared_lib_system_utils_audit.md) rather than duplicating them here.
