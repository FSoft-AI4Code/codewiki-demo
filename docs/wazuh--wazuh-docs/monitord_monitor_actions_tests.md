# Monitord Monitor Actions Tests

## Introduction

monitord_monitor_actions_tests is the CMocka unit-test module for Wazuh's native monitord agent-monitoring actions. It tests the action layer implemented by src/monitord/monitor_actions.c: disconnection detection, alert generation, stale-agent deletion, and log-rotation decisions.

The production behavior is documented in [monitord_agent_monitoring](monitord_agent_monitoring.md). This page focuses on the test harness, isolation seams, assertions, and failure-path coverage. Daemon scheduling and global configuration ownership are described in [monitord_lifecycle](monitord_lifecycle.md).

## Scope and position

~~~mermaid
flowchart LR
    T["monitord_monitor_actions_tests<br/>18 CMocka cases"] --> S["monitor_actions.c<br/>agent and log actions"]
    S --> DB["wazuh_db<br/>agent status and metadata"]
    S --> AUTH["os_auth<br/>remove stale agents"]
    S --> MQ["SendMSG<br/>local/secure queues"]
    S --> HASH["OSHash<br/>alert tracking"]
    S --> FS["stat and file helpers<br/>log-size checks"]
    S --> ROT["w_rotate_log<br/>rotation boundary"]
    T -. mocks .-> DB
    T -. expectations .-> AUTH
    T -. expectations .-> MQ
    T -. expectations .-> HASH
    T -. mocks .-> FS
~~~

This is a test boundary, not a runtime daemon. It does not test configuration parsing, the periodic scheduler, queue reconnection, or physical log rotation. See [monitord](monitord.md), [monitord_lifecycle](monitord_lifecycle.md), and [monitord_log_management](monitord_log_management.md) for those concerns.

## Harness architecture

~~~mermaid
graph TD
    Main["main()<br/>cmocka_run_group_tests"] --> Cases["18 test cases<br/>expect_* and will_return"]
    Cases --> Setup["setup_monitord()<br/>global-state reset"]
    Cases --> Teardown["teardown_monitord()<br/>restore state"]
    Cases --> SUT["monitor_actions.c"]
    SUT --> WDB["wdb_* wrappers"]
    SUT --> Auth["auth_* wrappers"]
    SUT --> Queue["SendMSG wrapper"]
    SUT --> Hash["OSHash_* wrappers"]
    SUT --> Stat["stat wrapper"]
    SUT --> Debug["logging wrappers"]
    SUT --> Rotate["monitord rotation wrapper"]
~~~

### Setup and teardown

Each registered case uses cmocka_unit_test_setup_teardown. setup_monitord:

- enables test_mode;
- clears the disconnection and alert thresholds;
- resets mond fields including a_queue, delete_old_agents, monitor_agents, rotate_log, size_rotate, and day_wait;
- resets mond_time_control counters and date fields.

teardown_monitord repeats the state cleanup and disables test_mode. This is important because mond, mond_time_control, and agents_to_alert_hash are global state. The CMocka state pointer is unused but retained for the framework callback signature.

## Interfaces under test

| Interface | Cases | Contract verified |
| --- | --- | --- |
| monitor_send_deletion_msg | success and queue failure | Formats OS_AG_REMOVED, uses LOCALFILE_MQ, and invalidates mond.a_queue after SendMSG failure. |
| monitor_send_disconnection_msg | success, missing agent, lookup failure, malformed input | Resolves name-ip, sends AG_DISCON_MSG through SECURE_MQ, and falls back to a removal alert if the agent disappeared. |
| monitor_agents_disconnection | one case | Queries newly disconnected agents and inserts their IDs into the alert hash. |
| monitor_agents_alert | active, missing-info, and message-sent cases | Clears reconnected/stale entries and emits a disconnection alert when due. |
| monitor_agents_deletion | success and three failure cases | Resolves IDs, authenticates to Authd, removes old agents, and handles lookup/Authd/DB failures. |
| monitor_logs | size false and size true | Selects the daily or size-check path and reaches the rotation boundary. |

Threshold arithmetic and scheduling are production concerns covered by [monitord_agent_monitoring](monitord_agent_monitoring.md); this suite supplies fixed timestamps and controlled collaborators.

## Alert and deletion flow

~~~mermaid
sequenceDiagram
    participant Test as CMocka case
    participant Action as monitor_actions.c
    participant DB as wdb_find_agent
    participant Queue as SendMSG wrapper
    participant Auth as Authd wrappers

    Test->>Action: monitor_send_disconnection_msg("Agent1-any")
    Action->>DB: find name=Agent1, ip=any
    alt agent found
        DB-->>Action: id 1
        Action->>Queue: AG_DISCON_MSG via SECURE_MQ
    else agent already removed
        DB-->>Action: -2
        Action->>Action: monitor_send_deletion_msg
        Action->>Queue: OS_AG_REMOVED via LOCALFILE_MQ
    end
    Test->>Action: monitor_agents_deletion
    Action->>Auth: get ID, auth_connect, auth_remove_agent, auth_close
    Auth-->>Action: success or failure
~~~

### Removal messages

test_monitor_send_deletion_msg_success verifies OS_AG_REMOVED formatting, ARGV0 as the local-message origin, LOCALFILE_MQ delivery, and preservation of a valid queue.

test_monitor_send_deletion_msg_fail forces SendMSG to return -1. It checks both diagnostics and mond.a_queue becoming -1 so the daemon can reconnect on a later cycle.

### Disconnection messages

The success case checks the Agent1-any parsing convention, wdb_find_agent lookup, header formatting as [001] (Agent1) any, and SECURE_MQ delivery. Other cases cover:

- SendMSG failure, including queue invalidation and diagnostics;
- wdb_find_agent returning -2, which switches to a removal alert;
- generic lookup failure, which logs and leaves the queue unchanged;
- an invalid or missing IP component;
- an overlong agent name, preventing unsafe message construction.

## Agent monitoring flows

~~~mermaid
flowchart TD
    Start["monitoring action"] --> D["monitor_agents_disconnection"]
    D --> Q1["wdb_disconnect_agents(now - threshold, synced)"]
    Q1 --> H["OSHash_Add(agent ID, timestamp)"]
    H --> A["monitor_agents_alert"]
    A --> I["wdb_get_agent_info(agent ID)"]
    I --> Status{"status/data"}
    Status -- active --> Drop["OSHash_Delete<br/>no alert"]
    Status -- missing --> Drop2["log failure and delete entry"]
    Status -- disconnected and due --> Alert["send disconnection/removal alert"]
    Alert --> Drop
    Drop --> Del["monitor_agents_deletion"]
    Drop2 --> Del
    Del --> Q2["wdb_get_agents_by_connection_status(disconnected)"]
    Q2 --> Due{"past deletion threshold?"}
    Due -- no --> End["leave registered"]
    Due -- yes --> Remove["resolve ID and remove through Authd"]
    Remove --> End2["send removal alert or report failure"]
~~~

### Disconnection tracking

test_monitor_agents_disconnection supplies IDs 13 and 5, terminated by -1, and a fixed current time. It verifies the expected keepalive cutoff and synced status passed to wdb_disconnect_agents. The first OSHash_Add succeeds and the second fails, exercising the alert-hash error diagnostic.

### Pending-agent alerts

- test_monitor_agents_alert_active returns active information and verifies that the pending entry is removed without an alert.
- test_monitor_agents_alert_agent_info_fail returns no DB information, verifies the diagnostic, and removes the stale entry.
- test_monitor_agents_alert_message_sent returns a disconnected agent, sets fixed thresholds and time, and verifies the complete secure alert path.

### Stale-agent deletion

The deletion cases use one disconnected agent, ID 13, and an agent-info JSON object. They verify:

- successful ID resolution, Authd connection, removal, and local removal alert;
- missing agent information and alert-hash cleanup;
- Authd connection failure and its diagnostic;
- failure to resolve the numeric ID, which stops before authentication.

Authd behavior is documented in [os_auth](os_auth.md); these tests verify only the monitord boundary calls and return handling.

## Log monitoring

~~~mermaid
flowchart LR
    T["monitor_logs(check_logs_size, path, path_json)"] --> C{"check_logs_size?"}
    C -- no --> R1["daily path<br/>day_wait and rotation settings"]
    C -- yes --> S1["stat(path)"]
    S1 --> S2["stat(path_json)"]
    S2 --> R2{"size_rotate exceeded?"}
    R2 -- no --> N["no rotation"]
    R2 -- yes --> W["w_rotate_log wrapper"]
    R1 --> W
~~~

test_monitor_logs_size_false exercises the non-size-check path with rotation enabled. test_monitor_logs_size_true configures a threshold and supplies successful stat results for both log paths. Actual rotation and retention belong to [monitord_log_management](monitord_log_management.md).

## Test inventory

| Area | Tests |
| --- | --- |
| Removal message | test_monitor_send_deletion_msg_success, test_monitor_send_deletion_msg_fail |
| Disconnection message | test_monitor_send_disconnection_msg_success, test_monitor_send_disconnection_msg_send_msg_fail, test_monitor_send_disconnection_msg_agent_removed, test_monitor_send_disconnection_msg_fail, test_monitor_send_disconnection_ip_fail, test_monitor_send_disconnection_name_size_fail |
| Disconnection detection | test_monitor_agents_disconnection |
| Alert evaluation | test_monitor_agents_alert_active, test_monitor_agents_alert_agent_info_fail, test_monitor_agents_alert_message_sent |
| Stale-agent deletion | test_monitor_agents_deletion_success, test_monitor_agents_deletion_agent_info_fail, test_monitor_agents_deletion_auth_fail, test_monitor_agents_deletion_agent_id_fail |
| Log checks | test_monitor_logs_size_false, test_monitor_logs_size_true |

## Mock and wrapper dependencies

~~~mermaid
graph LR
    Cases["test_monitor_actions.c"] --> CMocka["CMocka expectations"]
    Cases --> Mon["monitord_wrappers<br/>rotation seams"]
    Cases --> MQ["mq_op_wrappers<br/>SendMSG"]
    Cases --> DB["agent_op_wrappers<br/>wdb operations"]
    Cases --> Auth["auth_client_wrappers<br/>Authd client"]
    Cases --> Hash["hash_op_wrappers<br/>OSHash table"]
    Cases --> Net["os_net_wrappers"]
    Cases --> Stat["stat_wrappers"]
    Cases --> Debug["debug_op_wrappers"]
~~~

Important seams are __wrap_SendMSG; __wrap_wdb_find_agent; __wrap_wdb_get_agent_info; __wrap_wdb_disconnect_agents; __wrap_wdb_get_agents_by_connection_status; __wrap_auth_connect; __wrap_auth_remove_agent; __wrap_OSHash_Add, Begin, Next, and Delete; __wrap_stat; debug/error wrappers; and __wrap_w_rotate_log.

These are shared test doubles, not production dependencies. Their source organization is under src/unit_tests/wrappers and follows the wrapper groups listed above.

## Execution and maintenance notes

The executable is registered under the Unit_Tests_-_Monitord hierarchy as monitord_monitor_actions_tests. Its main function registers all 18 cases and returns cmocka_run_group_tests.

Update this document and the tests when changing message formats, queue types, queue invalidation, name-ip parsing, the -1 ID-array sentinel, Wazuh DB/Authd return values, global setup fields, or the monitor_logs/w_rotate_log boundary.

Because the suite uses global state and linker wrappers, leaked expectations or state can affect later cases. New tests should use the existing setup/teardown pair and explicitly configure every wrapped call they expect.

## Related documentation

- [monitord_agent_monitoring](monitord_agent_monitoring.md) — production implementation under test.
- [monitord_lifecycle](monitord_lifecycle.md) — scheduler, configuration, and shared globals.
- [monitord_log_management](monitord_log_management.md) — physical log rotation and retention.
- [monitord](monitord.md) — parent daemon architecture.
- [wazuh_db](wazuh_db.md) — agent-state database operations.
- [os_auth](os_auth.md) — Authd and agent registration/removal.
- [shared_lib](shared_lib.md) — queues, hashes, logging, filesystem, and common utilities.
- src/unit_tests/wrappers — shared CMocka wrapper infrastructure used by the suite.

## Summary

monitord_monitor_actions_tests verifies the action layer connecting monitord's agent-state decisions to Wazuh DB, Authd, message queues, hash-based alert tracking, and log checks. Its key value is failure-path coverage: queue failures, missing agents, DB failures, hash insertion errors, Authd failures, malformed identifiers, and filesystem-boundary behavior.
