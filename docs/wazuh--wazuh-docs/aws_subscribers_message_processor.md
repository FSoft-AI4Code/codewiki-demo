# AWS subscriber message processors

This document describes `wodles/aws/subscribers/sqs_message_processor.py`.

## Common processing

`AWSQueueMessageProcessor.extract_message_info` converts raw SQS records into internal dictionaries. It JSON-decodes each `Body`, preserves `ReceiptHandle` as `handle`, and adds the result of `parse_message`. The returned shape is normally:

```json
{
  "route": {"log_path": "...", "bucket_path": "..."},
  "handle": "..."
}
```

If a concrete parser cannot find the expected fields, it returns `raw_message` instead. This allows the queue layer to log and omit the item without confusing an arbitrary payload with an S3 object route.

## Concrete parsers

| Class | Expected notification | Route extraction |
|---|---|---|
| `AWSS3MessageProcessor` | Amazon S3 event notification | `Records[0].s3.object.key` and `Records[0].s3.bucket.name` |
| `AWSSSecLakeMessageProcessor` | Security Lake/EventBridge-style notification | `detail.object.key` and `detail.bucket.name` |

The S3 object key is not URL-decoded here; decoding is performed by `AWSSubscriberBucket.process_file` for regular S3 integrations. Security Lake processing passes the key through unchanged.

```mermaid
flowchart LR
    A[SQS message] --> B[JSON decode Body]
    B --> C{Processor strategy}
    C -->|S3| D[Records[0].s3]
    C -->|Security Lake| E[detail]
    D --> F[route + handle]
    E --> F
    D -.missing fields.-> G[raw_message]
    E -.missing fields.-> G
```

## Extension contract

To support another notification format, subclass `AWSQueueMessageProcessor` and implement `parse_message(message)`. The parser should return a `route` containing the bucket and object path when the message is actionable, or `raw_message` when it is not. The queue remains unchanged.

See [aws_subscribers_queue.md](aws_subscribers_queue.md) for orchestration and [aws_subscribers_s3_handlers.md](aws_subscribers_s3_handlers.md) for consumers of the route.
