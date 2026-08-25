# AWS S3 bucket log ingestion

The `aws_buckets_s3` module implements the S3-backed side of Wazuh's AWS log collection. It discovers objects, resumes from the last processed key, downloads and decompresses files, parses service-specific formats, normalizes event fields, and forwards events to Wazuh. It supports AWS-native service layouts as well as custom S3-delivered logs.

The module is consumed by the AWS integration entry point in `wodles/aws/aws_s3.py` and shares credentials, AWS clients, scheduling, messaging, and SQLite integration with the surrounding [aws_core](aws_core.md) module. The common bucket behavior is detailed in [aws_buckets_s3_core](aws_buckets_s3_core.md).

## Architecture

```mermaid
flowchart LR
    CLI[aws_s3.py / configuration] --> FACTORY[Bucket type selection]
    FACTORY --> BASE[AWSBucket]
    BASE --> LOGS[AWSLogsBucket]
    BASE --> CUSTOM[AWSCustomBucket]
    LOGS --> SERVICES[CloudTrail, Config, VPC Flow]
    CUSTOM --> FORMATS[GuardDuty, WAF, Umbrella, S3 access]
    CUSTOM --> LB[ALB, CLB, NLB]
    SERVICES --> S3[(Amazon S3)]
    FORMATS --> S3
    LB --> S3
    BASE --> DB[(SQLite processed-key database)]
    BASE --> MQ[Wazuh message queue]
```

The inheritance hierarchy separates orchestration from parsing:

```mermaid
classDiagram
    class WazuhAWSDatabase
    class AWSBucket
    class AWSLogsBucket
    class AWSCustomBucket
    class AWSCloudTrailBucket
    class AWSConfigBucket
    class AWSVPCFlowBucket
    class AWSGuardDutyBucket
    class AWSWAFBucket
    class AWSServerAccess
    class CiscoUmbrella
    class AWSLBBucket
    class AWSALBBucket
    class AWSCLBBucket
    class AWSNLBBucket
    WazuhAWSDatabase <|-- AWSBucket
    AWSBucket <|-- AWSLogsBucket
    AWSBucket <|-- AWSCustomBucket
    AWSLogsBucket <|-- AWSCloudTrailBucket
    AWSLogsBucket <|-- AWSConfigBucket
    AWSLogsBucket <|-- AWSVPCFlowBucket
    AWSCustomBucket <|-- AWSGuardDutyBucket
    AWSCustomBucket <|-- AWSWAFBucket
    AWSCustomBucket <|-- AWSServerAccess
    AWSCustomBucket <|-- CiscoUmbrella
    AWSCustomBucket <|-- AWSLBBucket
    AWSLBBucket <|-- AWSALBBucket
    AWSLBBucket <|-- AWSCLBBucket
    AWSLBBucket <|-- AWSNLBBucket
```

## Processing flow

```mermaid
sequenceDiagram
    participant Runner as AWS runner
    participant Bucket as Bucket handler
    participant S3 as S3 API
    participant DB as SQLite state
    participant Wazuh as Wazuh queue
    Runner->>Bucket: construct configured handler
    Bucket->>S3: check bucket and discover accounts/regions
    Bucket->>DB: read last processed key
    Bucket->>S3: list_objects_v2(StartAfter / continuation)
    loop each eligible object
        Bucket->>DB: already_processed?
        Bucket->>S3: download and decompress object
        Bucket->>Bucket: parse and normalize events
        Bucket->>Wazuh: send event or error alert
        Bucket->>DB: mark object complete
        opt delete_file
            Bucket->>S3: delete object
        end
    end
    Bucket->>DB: retain latest 500 records per scope
```

## Sub-modules

| Area | Responsibility | Detailed documentation |
|---|---|---|
| Common bucket engine | S3 traversal, pagination, markers, deduplication, error handling, event envelopes, and retention state | [aws_buckets_s3_core](aws_buckets_s3_core.md) |
| AWS service layouts | CloudTrail JSON, AWS Config date ordering/normalization, GuardDuty native and legacy layouts | [aws_buckets_s3_service_logs](aws_buckets_s3_service_logs.md) |
| Network and access logs | ALB/CLB/NLB, VPC Flow Logs, and S3 server-access parsing | [aws_buckets_s3_network_and_access_logs](aws_buckets_s3_network_and_access_logs.md) |
| Security and DNS logs | WAF JSON-lines/header normalization and Cisco Umbrella CSV variants | [aws_buckets_s3_security_and_dns_logs](aws_buckets_s3_security_and_dns_logs.md) |

## Format and state contracts

All handlers emit an AWS envelope containing `integration: aws`, `aws.log_info` metadata, and a normalized `aws.source`. The base implementation supports JSON arrays, concatenated JSON objects, and delimiter-separated text through subclass overrides. `skip_on_error` determines whether malformed objects produce an error event and processing continues, or terminate the collector.

The SQLite database is a resume ledger, not an event store. Keys are scoped by bucket path and, depending on the handler, account, region, and flow-log ID. `reparse` bypasses normal resume filtering while preserving the common traversal and parsing path. Maintenance removes entries older than the newest retained 500 records in each scope.

## Integration boundary

The module does not schedule itself or define the AWS CLI contract. Those concerns belong to [aws_core](aws_core.md). This module receives an already-resolved configuration and returns side effects through the AWS SDK, the Wazuh database helper, and the Wazuh messaging interface.
