# CloudWatch Logs service

The cloudwatch_logs module implements AWSCloudWatchLogs, the AWS service adapter that reads events from configured Amazon CloudWatch log groups and streams, forwards them to Wazuh analysisd, and persists per-stream progress in SQLite. It is selected by the AWS Python wodle when the service is configured as cloudwatchlogs.

The shared AWS authentication, botocore client creation, filtering options, SQLite lifecycle, message envelope, and Unix-queue transport are defined by [AWSService](base_service.md) and [AWS core](aws_core.md). The native scheduler and service dispatch are described in [AWS integration](aws.md).

## Position in the system

~~~mermaid
graph TB
    C["ossec.conf<br/>AWS wodle configuration"] --> D["wazuh-modulesd<br/>AWS scheduler"]
    D --> E["aws_s3.py<br/>service dispatcher"]
    E --> S["AWSCloudWatchLogs"]
    S --> B["AWSService<br/>shared AWS runtime"]
    B --> AWS["CloudWatch Logs API<br/>boto3 client"]
    B --> F["common event filtering"]
    S --> DB["aws_service.db<br/>cloudwatch_logs table"]
    S --> Q["Wazuh Unix queue"]
    Q --> A["analysisd<br/>and alert pipeline"]
~~~

AWSCloudWatchLogs is a leaf adapter in the aws_services package:

~~~mermaid
classDiagram
    class WazuhAWSDatabase {
        AWS sessions and credentials
        SQLite lifecycle
        filtering
        send_msg()
    }
    class AWSService {
        service_name
        region
        reparse
        default_date
        event_should_be_skipped()
    }
    class AWSCloudWatchLogs {
        log_group_list
        remove_log_streams
        only_logs_after_millis
        get_alerts()
        get_log_streams()
        get_alerts_within_range()
        purge_db()
    }
    class aws_tools {
        debug()
        error()
    }
    class CloudWatchLogsClient {
        describe_log_streams()
        get_log_events()
        delete_log_stream()
    }
    WazuhAWSDatabase <|-- AWSService
    AWSService <|-- AWSCloudWatchLogs
    AWSCloudWatchLogs --> aws_tools
    AWSCloudWatchLogs --> CloudWatchLogsClient
~~~

## Responsibilities

The adapter performs five service-specific tasks:

1. Parse the configured comma-separated log-group list and collection date.
2. Enumerate all streams in each configured log group, including paginated describe_log_streams responses.
3. Read events incrementally with CloudWatch nextForwardToken, timestamp bounds, and startFromHead=True.
4. Forward accepted event messages to Wazuh analysisd.
5. Reconcile SQLite state with AWS and optionally delete processed streams.

It does not own AWS credentials, STS role handling, retry configuration, or message formatting. Those responsibilities remain in the shared [AWS service base](base_service.md) and [AWS core](aws_core.md).

## Construction and configuration

The constructor accepts shared AWS settings plus CloudWatch-specific options:

| Parameter | Behavior |
| --- | --- |
| reparse | If true, rereads the configured historical range instead of relying only on the saved continuation token. |
| access_key, secret_key, profile | Forwarded to the inherited AWS integration. |
| iam_role_arn, iam_role_duration | Forwarded for assumed-role authentication. |
| only_logs_after | Optional YYYYMMDD date converted to UTC epoch milliseconds. |
| account_alias, region | Shared account and region identity. |
| aws_log_groups | Comma-separated group names; empty entries are discarded. |
| remove_log_streams | Deletes each stream after its events are processed. |
| discard_field, discard_regex | Shared event filtering options. |
| sts_endpoint, service_endpoint | Optional endpoint overrides. |

The adapter calls the base constructor with db_table_name='cloudwatch_logs' and service_name='cloudwatchlogs'. It then stores the parsed log groups, deletion policy, and date boundary. When no only_logs_after value is supplied, it uses the inherited default_date converted to milliseconds.

~~~mermaid
sequenceDiagram
    participant D as AWS dispatcher
    participant C as AWSCloudWatchLogs.__init__
    participant B as AWSService
    participant I as WazuhAWSDatabase
    D->>C: construct service options
    C->>B: initialize shared AWS service
    B->>I: create session/client and DB runtime
    I-->>B: shared state ready
    B-->>C: inherited service state
    C->>C: split log groups
    C->>C: convert only_logs_after to UTC milliseconds
~~~

The dispatcher chooses this adapter from the --service cloudwatchlogs path; see [AWS core service dispatch](aws_core.md#service-mode).

## Checkpoint database

The adapter creates a cloudwatch_logs table in the inherited AWS SQLite database. The table key is the tuple (aws_region, aws_log_group, aws_log_stream).

~~~sql
CREATE TABLE cloudwatch_logs (
    aws_region text NOT NULL,
    aws_log_group text NOT NULL,
    aws_log_stream text NOT NULL,
    next_token text,
    start_time integer,
    end_time integer,
    PRIMARY KEY (aws_region, aws_log_group, aws_log_stream)
);
~~~

The stored values mean:

| Column | Meaning |
| --- | --- |
| next_token | CloudWatch nextForwardToken for continuing the stream. |
| start_time | Lowest timestamp observed among accepted events for the stream. |
| end_time | Highest timestamp observed among accepted events for the stream. |

get_data_from_db() reads one checkpoint. save_data_db() first attempts an insert and falls back to an update on a primary-key collision. purge_db() removes rows for streams that no longer exist in AWS.

~~~mermaid
stateDiagram-v2
    [*] --> NoCheckpoint
    NoCheckpoint --> Reading: enumerate stream
    Reading --> Checkpointed: events accepted
    Checkpointed --> Reading: next scheduled run
    Checkpointed --> Purged: stream absent from AWS
    Purged --> [*]
    state Reading {
        [*] --> RequestRange
        RequestRange --> SaveToken
        SaveToken --> RequestRange: response has events
        SaveToken --> [*]: response events empty
    }
~~~

## Main collection flow

get_alerts() initializes the table, iterates configured groups, discovers streams, loads each stream checkpoint, reads missing ranges, saves merged values, optionally deletes streams, and purges stale rows. The database is closed in a finally block even when an AWS request raises an error.

~~~mermaid
flowchart TD
    S["get_alerts()"] --> I["init_db(create cloudwatch_logs)"]
    I --> G["For each configured log group"]
    G --> L["get_log_streams(group)"]
    L --> M["For each log stream"]
    M --> R["Read checkpoint from SQLite"]
    R --> B["Determine before-range and after-range"]
    B --> P["get_alerts_within_range()"]
    P --> U["update_values()"]
    U --> W["insert or update checkpoint"]
    W --> X{"remove_log_streams?"}
    X -->|yes| Z["delete_log_stream()"]
    X -->|no| N["next stream"]
    Z --> N
    N --> Y["purge_db(group)"]
    Y --> G
    G -->|all groups complete| Q["close_db()"]
~~~

### Range selection

For a stream with no checkpoint, collection begins at only_logs_after_millis, or at the inherited default date when no explicit date is configured. For an existing checkpoint:

- reparse=True rereads from the configured/default start boundary.
- If the checkpoint start_time is newer than the requested start, a result_before pass reads the gap before the stored range.
- If end_time exists and is newer than the configured only_logs_after boundary, the normal continuation begins at end_time + 1 with the saved token.

This two-pass design handles both backfilled events and forward continuation while retaining the minimum start timestamp and maximum end timestamp.

## Reading events from CloudWatch

get_alerts_within_range() repeatedly calls get_log_events() until the API returns an empty events list. Requests include the following values when they are not None:

~~~text
logGroupName, logStreamName, nextToken,
startTime, endTime, startFromHead=True
~~~

After each response, nextForwardToken becomes the next request token. Each event message is processed as follows:

~~~mermaid
flowchart LR
    API["get_log_events()"] --> E{"events present?"}
    E -->|no| DONE["Return token and range"]
    E -->|yes| J{"message is JSON?"}
    J -->|yes| F["event_should_be_skipped(json)"]
    J -->|no| R["match discard regex against raw message"]
    F --> K{"discarded?"}
    R --> K
    K -->|yes| SKIP["Skip event"]
    K -->|no| SEND["send_msg(event_msg, dump_json=False)"]
    SKIP --> NEXT["Update token and request next page"]
    SEND --> RANGE["Update min start/max end timestamps"]
    RANGE --> NEXT
    NEXT --> API
~~~

JSON messages are passed to the inherited structured filtering path. Non-JSON messages are tested directly against self.discard_regex; this preserves filtering for plain-text CloudWatch events. Accepted messages are sent unchanged as the event payload, with JSON dumping disabled because the CloudWatch message is already the source payload.

The returned range is:

~~~text
{
    "token": nextForwardToken,
    "start_time": minimum accepted event timestamp,
    "end_time": maximum accepted event timestamp
}
~~~

If no accepted events are found, the method retains the input-derived bounds and still returns the latest token.

## Stream discovery and pagination

get_log_streams() calls describe_log_streams(logGroupName=...), follows every response nextToken, and returns stream names. The method treats endpoint failures as logged errors and returns an empty list; CloudWatch client errors terminate the process with exit code 16. Other exceptions are logged as an inaccessible or nonexistent group and also result in an empty list.

~~~mermaid
sequenceDiagram
    participant C as CloudWatch adapter
    participant API as CloudWatch Logs
    participant DB as SQLite
    C->>API: describe_log_streams(group)
    API-->>C: streams + nextToken?
    loop while nextToken exists
        C->>API: describe_log_streams(group, nextToken)
        API-->>C: more streams + nextToken?
    end
    C->>DB: compare discovered streams with saved streams
    DB-->>C: stale stream rows
    C->>DB: delete stale rows
~~~

## Optional stream deletion

When remove_log_streams is enabled, remove_aws_log_stream() invokes delete_log_stream() after the stream’s checkpoint has been saved. A CloudWatch ClientError is fatal with exit code 16; unexpected exceptions are logged at debug level and do not stop the overall iteration.

This option changes the source of truth: after deletion, the stream disappears from AWS and its local row is removed on the subsequent purge_db() reconciliation.

## Error and recovery behavior

| Operation | Endpoint unavailable | AWS client error | Other exception |
| --- | --- | --- | --- |
| describe_log_streams | Log error; return no streams | Log error; exit 16 | Debug log; return no streams |
| get_log_events | Retry indefinitely by continuing the request loop | Log error; exit 16 | Not separately caught in this method |
| delete_log_stream | Covered by the generic exception path | Log error; exit 16 | Debug log; continue |
| SQLite insert | N/A | N/A | IntegrityError triggers update |

The EndpointConnectionError branch in get_alerts_within_range() uses continue, so the same request is retried until it succeeds. There is no local retry counter in this adapter; broader botocore retry configuration is supplied by [AWS core](aws_core.md).

## Operational considerations

- Use stable, explicit log-group names; empty group entries are silently removed during construction.
- Keep aws_service.db durable. Losing the cloudwatch_logs table causes the next run to start from the configured/default date and may reread old events.
- only_logs_after is interpreted as midnight UTC on the supplied date.
- Checkpoint timestamps are based on accepted events, so discarded events do not advance the stored event range, although the CloudWatch continuation token still advances.
- Deleting streams is irreversible at the AWS source level and should be enabled only when retention behavior is intentional.
- Region, credentials, IAM role, endpoint, and common filtering failures should be diagnosed using the shared [AWS service base](base_service.md) and [AWS core](aws_core.md) documentation.

## Source reference

| File | Responsibility |
| --- | --- |
| wodles/aws/services/cloudwatchlogs.py | AWSCloudWatchLogs implementation documented here. |
| wodles/aws/services/aws_service.py | Shared service adapter and inherited behavior; see [AWS service base](base_service.md). |
| wodles/aws/wazuh_integration.py | AWS sessions, SQLite connection, filtering, and Wazuh transport; see [AWS core](aws_core.md). |
| wodles/aws/aws_s3.py | Service selection and invocation; see [AWS core](aws_core.md). |
| wodles/aws/aws_tools.py | AWS logging and validation helpers. |
