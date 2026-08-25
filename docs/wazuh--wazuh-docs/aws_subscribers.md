# AWS subscribers

The `aws_subscribers` module consumes AWS notifications from Amazon SQS, locates the referenced objects in Amazon S3, converts their contents into normalized events, and forwards those events to Wazuh Analysisd. It supports ordinary S3 log notifications, AWS Security Hub exports, and AWS Security Lake parquet events.

## Architecture overview

The module is an adapter pipeline. `AWSSQSQueue` controls polling and acknowledgement, a message processor translates provider-specific notification schemas into a common route, and a bucket handler retrieves and transforms the referenced object.

```mermaid
flowchart LR
    AWS[AWS notification producer] --> SQS[Amazon SQS]
    SQS --> Q[AWSSQSQueue]
    Q --> P{Message processor}
    P -->|S3 notification| R1[Bucket + object route]
    P -->|Security Lake notification| R2[Bucket + object route]
    R1 --> H1[AWSSubscriberBucket]
    R2 --> H2[AWSSLSubscriberBucket or AWSSecurityHubSubscriberBucket]
    H1 --> A[Analysisd]
    H2 --> A
    Q -->|delete after processing| SQS
```

## Sub-modules

- [Queue orchestration](aws_subscribers_queue.md) — `AWSSQSQueue`, AWS client setup, long polling, routing delegation, and post-processing deletion.
- [Message processors](aws_subscribers_message_processor.md) — `AWSQueueMessageProcessor`, `AWSS3MessageProcessor`, and `AWSSSecLakeMessageProcessor`.
- [S3 handlers](aws_subscribers_s3_handlers.md) — `AWSS3LogHandler`, `AWSSubscriberBucket`, `AWSSLSubscriberBucket`, and `AWSSecurityHubSubscriberBucket`.

## End-to-end data flow

```mermaid
sequenceDiagram
    participant Queue as AWSSQSQueue
    participant SQS as SQS
    participant Parser as MessageProcessor
    participant S3 as BucketHandler/S3
    participant AD as Analysisd
    Queue->>SQS: receive_message (long poll)
    SQS-->>Queue: Body + ReceiptHandle
    Queue->>Parser: extract_message_info
    Parser-->>Queue: route + handle
    Queue->>S3: process_file(route)
    S3->>S3: retrieve, decompress/read, normalize, filter
    S3->>AD: send_msg(event)
    S3-->>Queue: completed
    Queue->>SQS: delete_message(handle)
```

## System fit

The module sits below the AWS Wodle entry points and above the shared AWS integration layer. The upstream AWS service configuration selects a queue, processor, and handler combination. The shared `wazuh_integration.WazuhIntegration` provides credentials/role handling, AWS clients, object decompression, discard rules, and Analysisd delivery; those responsibilities are referenced rather than duplicated in the sub-module documents.

The principal invariant is acknowledgement ordering: a queue receipt is deleted only after the selected handler returns from processing. Unsupported or malformed notification payloads are logged by the queue layer and are not interpreted as S3 routes.

## Supported combinations

| Notification | Processor | Handler | Object representation |
|---|---|---|---|
| Standard S3 event | `AWSS3MessageProcessor` | `AWSSubscriberBucket` | JSONL, JSON, CSV, or text |
| Security Hub S3 event | `AWSS3MessageProcessor` | `AWSSecurityHubSubscriberBucket` | JSON event records |
| Security Lake event | `AWSSSecLakeMessageProcessor` | `AWSSLSubscriberBucket` | Parquet |

## Maintenance notes

New notification schemas should normally add a message processor; new object formats should add or extend a bucket handler. Keep the queue's strategy interfaces stable, preserve receipt handles through parsing, and retain the process-then-delete ordering to avoid acknowledging objects before their events have been handed to Analysisd.
