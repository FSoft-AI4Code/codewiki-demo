# Agent upgrade parsing

The `agent_upgrade_parsing` module defines and tests the translation boundary for Wazuh agent-upgrade messages. It converts JSON requests into command discriminators, sentinel-terminated agent-ID arrays, and command-specific task structures; it converts internal results and agent replies back into JSON or status values; and it reports malformed input through structured error responses.

The implementation is exercised by `src/unit_tests/wazuh_modules/agent_upgrade/test_wm_agent_upgrade_parsing.c`. The production parser declarations are provided by `wm_agent_upgrade_parsing.h`, while task structures and destructors come from `wm_agent_upgrade_tasks.h`. Scheduling, validation, transfer, and lifecycle behavior are intentionally outside this module; see [agent_upgrade_module](agent_upgrade_module.md), [agent_upgrade_manager](agent_upgrade_manager.md), [agent_upgrade_commands](agent_upgrade_commands.md), and [agent_upgrade_main](agent_upgrade_main.md).

## Role in the upgrade system

Parsing is the protocol adapter between the manager listener/task-manager callers and the upgrade command implementation. It has no socket loop, database access, package-transfer logic, or installer execution of its own.

```mermaid
flowchart LR
    Caller[API / task manager / cluster caller] --> Listener[Manager upgrade listener]
    Listener --> Parse[agent_upgrade_parsing]
    Parse -->|command + agents + task| Commands[Upgrade command handlers]
    Commands --> Runtime[Scheduling, validation, transfer]
    Runtime --> Results[Task and agent results]
    Results --> Serialize[Response serializers]
    Serialize --> Listener
    Parse -. malformed input .-> Error[Structured error JSON]
```

## Architecture and dependencies

```mermaid
graph TD
    TEST[test_wm_agent_upgrade_parsing.c]
    API[wm_agent_upgrade_parsing.h]
    TASKS[wm_agent_upgrade_tasks.h]
    JSON[cJSON]
    XML[OS_ReadXML / OS_GetOneContentforElement]
    LOG[Wazuh error logging]
    MEM[os_malloc / os_strdup / os_free]
    MAN[agent_upgrade_manager]
    CMD[agent_upgrade_commands]
    TEST --> API
    TEST --> TASKS
    API --> JSON
    API --> XML
    API --> LOG
    API --> MEM
    MAN --> API
    CMD --> API
    CMD --> TASKS
```

The test suite replaces external XML and logging calls with CMocka wrappers. `__wrap_OS_ReadXML` returns a scripted result, `__wrap_OS_GetOneContentforElement` supplies the node name, and `__wrap_OS_ClearXML` is a no-op. This isolates construction of task-module messages from the host configuration and filesystem.

## Public parsing responsibilities

| Function | Input | Output / contract |
| --- | --- | --- |
| `wm_agent_upgrade_parse_message` | JSON command message | Returns a `WM_UPGRADE_*` discriminator or `OS_INVALID`; fills a task pointer, agent IDs, and optional structured error string. |
| `wm_agent_upgrade_parse_agents` | JSON array | Allocates integer IDs terminated by `-1`; rejects non-number entries and reports `Agent id not recognized`. |
| `wm_agent_upgrade_parse_upgrade_command` | `parameters` object | Builds `wm_upgrade_task` with repository, version, HTTP, force, package type, and optional package metadata. |
| `wm_agent_upgrade_parse_upgrade_custom_command` | `parameters` object | Builds `wm_upgrade_custom_task` with WPK file path and installer. |
| `wm_agent_upgrade_parse_upgrade_agent_status` | `parameters` object | Builds `wm_upgrade_agent_status_task` with numeric error, message, and status. |
| `wm_agent_upgrade_parse_agent_response` | Legacy text response | Maps `ok <data>` to `0`, `err <message>` to `-1`, and unknown/NULL input to `-1`. |
| `wm_agent_upgrade_parse_agent_upgrade_command_response` | JSON agent response | Reads `error` and `message`; returns `0` for success, the agent error code for known failures, and `-1` for unknown/malformed responses. |
| `wm_agent_upgrade_parse_data_response` | Error code, message, optional agent ID | Builds an object containing `error` and `message`, adding `agent` only when supplied. |
| `wm_agent_upgrade_parse_response` | Error code and cJSON data | Builds a standard response with `error`, `message`, and `data`; success uses message `Success`. |
| `wm_agent_upgrade_parse_task_module_request` | Command, agent array, optional status/error | Builds a task-module JSON request with origin, command, and parameters. The origin name is read from XML configuration. |

## Command message flow

The top-level parser first decodes JSON, verifies the required `command` and `parameters` fields, parses `agents`, and then dispatches command-specific parameter parsing. Agent IDs are parsed before the task payload, which explains why a task-parameter failure may still return a valid allocated agent array.

```mermaid
flowchart TD
    S[Raw message] --> J{Valid JSON object?}
    J -->|no| E1[error 1: Could not parse message JSON]
    J -->|yes| R{command and parameters present?}
    R -->|no| E2[error 2: required parameters missing]
    R -->|yes| A[Parse agents array]
    A -->|invalid type / empty| E3[error 3: JSON parameter not recognized]
    A -->|success| C{command}
    C -->|upgrade| U[Parse wm_upgrade_task]
    C -->|upgrade_custom| UC[Parse custom task]
    C -->|upgrade_update_status| US[Parse agent status task]
    C -->|upgrade_result| UR[No task payload]
    C -->|unknown| E4[error 3: no action defined]
    U --> O[Return discriminator + task + IDs]
    UC --> O
    US --> O
    UR --> O
    U -->|parameter error| E3
    UC -->|parameter error| E3
    US -->|parameter error| E3
```

### Supported command discriminators

| JSON `command` | Return value | Parsed payload |
| --- | --- | --- |
| `upgrade` | `WM_UPGRADE_UPGRADE` | `wm_upgrade_task` |
| `upgrade_custom` | `WM_UPGRADE_UPGRADE_CUSTOM` | `wm_upgrade_custom_task` |
| `upgrade_update_status` | `WM_UPGRADE_AGENT_UPDATE_STATUS` | `wm_upgrade_agent_status_task` |
| `upgrade_result` | `WM_UPGRADE_RESULT` | No task payload; agent IDs are retained. |

An unknown command returns `OS_INVALID`. The parser logs error `8102`, but exposes the caller-facing error as a top-level error `3` with a `data` array containing a parameter-recognition message.

## Parameter semantics and defaults

All command-specific fields are optional at this parsing layer unless the enclosing command requires them. Missing fields receive safe defaults rather than causing an error:

* Standard upgrade: repository, version, package type, WPK file, and SHA-1 are `NULL`; `use_http` and `force_upgrade` are `false`.
* Custom upgrade: file path and installer are `NULL`.
* Agent status: `error` defaults to `0`; message and status are `NULL`.
* Agent lists: an empty array produces an allocated array whose first value is `-1`, but an empty list is rejected by the complete message parser as missing required target agents.

When a field is present, its type is strict. Repository/version/package/file/installer/message/status must be strings; `error` must be numeric; `use_http` and `force_upgrade` must be JSON booleans; and `package_type` must be `rpm` or `deb`.

```mermaid
classDiagram
    class wm_upgrade_task {
        +char* wpk_repository
        +char* custom_version
        +bool use_http
        +bool force_upgrade
        +char* package_type
        +char* wpk_file
        +char* wpk_sha1
    }
    class wm_upgrade_custom_task {
        +char* custom_file_path
        +char* custom_installer
    }
    class wm_upgrade_agent_status_task {
        +int error_code
        +char* message
        +char* status
    }
    class wm_agent_upgrade_parse_message {
        +command discriminator
        +int[] agent_ids[-1]
        +void* task
        +char* error
    }
    wm_agent_upgrade_parse_message --> wm_upgrade_task
    wm_agent_upgrade_parse_message --> wm_upgrade_custom_task
    wm_agent_upgrade_parse_message --> wm_upgrade_agent_status_task
```

## Response and serialization flow

```mermaid
sequenceDiagram
    participant L as Manager listener
    participant P as Parser
    participant H as Command handler
    participant A as Agent

    L->>P: parse_message(JSON)
    P-->>L: discriminator, IDs, task
    L->>H: dispatch parsed command
    H->>A: upgrade protocol command
    A-->>H: legacy or JSON response
    H->>P: parse_agent_response(...)
    P-->>H: status/data/error
    H->>P: parse_response / parse_data_response
    P-->>L: response JSON
```

Standard success responses use the shape `{"error":0,"message":"Success","data":...}`. Data is normalized into an array by `wm_agent_upgrade_parse_response`; the tests cover both array and object input. Agent-scoped error objects contain `error`, `message`, and optionally `agent`. The absence of an agent ID is represented by omission of the `agent` property, not a null value.

Legacy agent replies are text-based: `ok ` with no payload is still successful and yields an empty string; `err ` yields `-1` and logs error `8116`. The JSON agent-command response uses its numeric `error` field, while a response without recognized fields logs `8117` and returns `-1`.

## Task-module request construction

`wm_agent_upgrade_parse_task_module_request` creates an internal request sent to the upgrade task module. It reads the current node name through XML configuration and emits a stable origin descriptor.

```mermaid
flowchart LR
    C[command selector] --> R[Build request]
    IDs[agent ID array] --> R
    XML[XML node lookup] --> OR[origin.name]
    OR --> R
    STATUS[optional status] --> R
    ERR[optional error_msg] --> R
    R --> OUT[origin + command + parameters JSON]
```

The request includes `origin.module = "upgrade_module"`, `command = "upgrade_custom"` for the tested command value, and an `agents` array. `status` and `error_msg` are omitted when NULL. If XML cannot be read, the origin name becomes an empty string while the rest of the request remains constructible.

## Error model

Parsing errors have two layers:

1. Internal diagnostic logs identify the exact validation failure, for example `8101` for invalid JSON, `8102` for an unknown command, `8103` for invalid parameter data, and `8107` for missing required fields.
2. Caller-facing JSON uses a compact error code and a `data` array. Typical values are error `1` for invalid JSON, error `2` for missing required fields, and error `3` for unrecognized command parameters.

```json
{
  "error": 3,
  "data": [{"error": 3, "message": "Parameter \"use_http\" should be true or false"}],
  "message": "JSON parameter not recognized"
}
```

The parser returns `OS_INVALID` for failures and leaves task outputs NULL when task construction fails. If agent IDs were parsed successfully before the task failure, the ID array remains available to the caller and must be freed by the caller.

## Ownership and cleanup

The parser allocates response JSON, error strings, agent-ID arrays, and task structures. The test fixtures make the ownership rules explicit:

* `teardown_json` deletes cJSON roots.
* `teardown_string` frees allocated strings with `os_free`.
* `teardown_parse_agents` frees the error and ID array.
* `teardown_parse_upgrade`, `teardown_parse_upgrade_custom`, and `teardown_parse_upgrade_agent_status` free both errors and their corresponding task through the task destructor.

Callers should use the matching task destructor from [agent_upgrade_commands](agent_upgrade_commands.md) or [agent_upgrade_module](agent_upgrade_module.md), and should not free nested task strings independently.

## Test coverage

```mermaid
mindmap
  root((agent_upgrade_parsing tests))
    Response builders
      data response with agent
      data response without agent
      array/object response data
      task-module request
    Agent replies
      legacy ok/err
      JSON ok/err
      empty and unknown payloads
    Input arrays
      valid IDs
      empty IDs
      non-number ID
    Task parameters
      standard upgrade
      custom upgrade
      agent status
      defaults
      strict type/value errors
    Top-level messages
      upgrade
      upgrade_custom
      update status
      result
      malformed JSON
      missing fields
      unknown command
```

The CMocka `main` registers each case with the appropriate teardown fixture. Wrapper expectations verify not only return values but also diagnostic log tags and messages. This makes the suite a protocol-contract test: changes to JSON field names, defaults, error codes, response shape, or allocation behavior are likely to surface here before affecting manager scheduling or agent transfer.

## Related modules

* [agent_upgrade_manager](agent_upgrade_manager.md) — local socket listener and dispatch boundary.
* [agent_upgrade_commands](agent_upgrade_commands.md) — manager command handlers, task callbacks, and result aggregation.
* [agent_upgrade_module](agent_upgrade_module.md) — end-to-end manager/agent workflow, package transfer, and validation.
* [agent_upgrade_com](agent_upgrade_com.md) — agent-side command execution after parsing.
* [agent_upgrade_main](agent_upgrade_main.md) — module lifecycle and configuration dump.
* [task_manager_module](task_manager_module.md) — durable upgrade task status handling.
