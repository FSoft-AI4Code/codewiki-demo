# Google Cloud Integration Module

## Introduction

The Google Cloud Integration module is designed to collect and process logs and events from various Google Cloud Platform (GCP) services. This integration enables Wazuh to monitor and analyze activities within a GCP environment, providing visibility into security-relevant events. The module can ingest data from Google Cloud Storage (GCS) buckets and Google Cloud Pub/Sub subscriptions.

## Architecture

The Google Cloud Integration module is composed of several key components that work together to fetch, process, and forward logs to the Wazuh analysis engine. The architecture is designed to be extensible, allowing for the integration of various GCP services.

```mermaid
graph TD
    subgraph Google Cloud
        GCS[Google Cloud Storage]
        PubSub[Google Cloud Pub/Sub]
    end

    subgraph Wazuh
        subgraph Google Cloud Integration Module
            WazuhGCloudIntegration((WazuhGCloudIntegration))
            WazuhGCloudBucket((WazuhGCloudBucket))
            GCSAccessLogs((GCSAccessLogs))
            WazuhGCloudSubscriber((WazuhGCloudSubscriber))
        end
        Analysisd[Analysisd]
    end

    GCS -- Logs --> GCSAccessLogs
    PubSub -- Messages --> WazuhGCloudSubscriber
    GCSAccessLogs -- Inherits from --> WazuhGCloudBucket
    WazuhGCloudBucket -- Inherits from --> WazuhGCloudIntegration
    WazuhGCloudSubscriber -- Inherits from --> WazuhGCloudIntegration
    WazuhGCloudIntegration -- Sends formatted events --> Analysisd
```

### Core Components

- **WazuhGCloudIntegration**: The base class for all Google Cloud integrations. It handles the communication with the Wazuh analysis engine (`analysisd`) through a socket connection. See [Communication Layer](Communication Layer.md) for more details.
- **WazuhGCloudBucket**: A subclass of `WazuhGCloudIntegration` that provides the core functionality for retrieving logs from GCS buckets. It maintains a local SQLite database (`gcloud.db`) to keep track of processed log files, preventing data duplication.
- **GCSAccessLogs**: A specific implementation of `WazuhGCloudBucket` for processing GCS access logs. It demonstrates how to extend the base bucket class to handle specific log formats.
- **WazuhGCloudSubscriber**: A subclass of `WazuhGCloudIntegration` responsible for pulling messages from a Google Cloud Pub/Sub subscription. This is used for real-time event ingestion.

## Component Interaction

The following diagram illustrates the interaction between the components when processing logs from a GCS bucket.

```mermaid
sequenceDiagram
    participant User as User/Configuration
    participant GCSAccessLogs as GCSAccessLogs
    participant WazuhGCloudBucket as WazuhGCloudBucket
    participant GCS as Google Cloud Storage
    participant DB as gcloud.db
    participant Analysisd as Wazuh Analysisd

    User->>GCSAccessLogs: Instantiate with credentials, bucket name, etc.
    GCSAccessLogs->>WazuhGCloudBucket: __init__()
    WazuhGCloudBucket->>WazuhGCloudBucket: check_permissions()
    WazuhGCloudBucket->>GCS: get_bucket()
    GCS-->>WazuhGCloudBucket: Bucket object
    WazuhGCloudBucket->>WazuhGCloudBucket: process_data()
    WazuhGCloudBucket->>DB: init_db()
    WazuhGCloudBucket->>DB: _get_last_creation_time()
    DB-->>WazuhGCloudBucket: last_creation_time
    WazuhGCloudBucket->>GCS: list_blobs()
    GCS-->>WazuhGCloudBucket: List of blobs
    loop For each new blob
        WazuhGCloudBucket->>GCSAccessLogs: process_blob(blob)
        GCSAccessLogs->>GCS: download_as_text()
        GCS-->>GCSAccessLogs: Blob content
        GCSAccessLogs->>GCSAccessLogs: load_information_from_file()
        GCSAccessLogs-->>WazuhGCloudBucket: List of events
        loop For each event
            WazuhGCloudBucket->>Analysisd: send_msg(formatted_event)
        end
    end
    WazuhGCloudBucket->>DB: _update_last_processed_files()
```

## Data Flow

The data flow from Google Cloud services to the Wazuh analysis engine is as follows:

```mermaid
graph TD
    A[Google Cloud Service] --> B{Data Source};
    B --> C[GCS Bucket];
    B --> D[Pub/Sub Topic];

    C --> E[WazuhGCloudBucket];
    D --> F[WazuhGCloudSubscriber];

    subgraph Wazuh Agent
        E --> G{Process Data};
        F --> G;
        G --> H[Format Message];
        H --> I[Send to Analysisd];
    end

    I --> J((Wazuh Analysisd));
```

1.  **Data Generation**: Google Cloud services generate logs and events.
2.  **Data Collection**: These logs are collected in either a GCS bucket or a Pub/Sub topic.
3.  **Data Ingestion**:
    - `WazuhGCloudBucket` periodically scans the specified GCS bucket for new log files.
    - `WazuhGCloudSubscriber` pulls new messages from the specified Pub/Sub subscription.
4.  **Data Processing**: The integration module processes the collected data, parsing and formatting it into a JSON structure that Wazuh can analyze.
5.  **Event Forwarding**: The formatted events are sent to the Wazuh analysis engine via a secure socket connection.

## Dependencies

The Google Cloud Integration module relies on several other modules within the Wazuh framework:

- **[Communication Layer](Communication Layer.md)**: For sending events to the `analysisd` process.
- **[Database Connectivity](Database Connectivity.md)**: The `WazuhGCloudBucket` component uses a local SQLite database to track the state of processed files.
- **[Core Framework](Core Framework.md)**: Utilizes core utilities and the overall Wazuh framework structure.
