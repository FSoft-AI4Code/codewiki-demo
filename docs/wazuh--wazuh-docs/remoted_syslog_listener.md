# Remoted Syslog Listener

## Introduction

The **Remoted Syslog Listener** is a small but focused subsystem of the Wazuh `remoted` daemon that allows the manager to receive **third-party syslog messages** over the network (in addition to the native, encrypted Wazuh agent protocol) and forward them into the manager's internal analysis pipeline. It implements two independent network listeners — one for **UDP syslog** and one for **TCP syslog** — that accept plain-text syslog datagrams/streams from external devices (firewalls, network appliances, switches, etc.), apply IP allow/deny filtering, strip the optional RFC3164 `<PRI>` header, and inject the resulting message into the local Wazuh queue (`ossec/queue/sockets/queue`) so it can be picked up by `analysisd` like any other event.

This module is a leaf component of the larger `remoted` daemon (see [remoted_state_metrics.md](remoted_state_metrics.md), [remoted_networking.md](remoted_networking.md), and [remoted_lifecycle.md](remoted_lifecycle.md) for sibling subsystems), and it depends on shared infrastructure such as the message queue API and IP-matching utilities documented in [shared_lib.md](shared_lib.md).

## Purpose & Scope

| Aspect | Description |
|---|---|
| **Module** | `remoted_syslog_listener` |
| **Location** | `src/remoted/syslog.c`, `src/remoted/syslogtcp.c` |
| **Parent daemon** | `remoted` (Wazuh Remote Daemon) |
| **Primary responsibility** | Accept raw syslog traffic (UDP/TCP) from non-Wazuh sources and relay it to the local analysis queue |
| **Consumers of output** | `analysisd` (via `queue/sockets/queue`), further documented in the Agent & Manager Native Daemons module tree |

The listener is an **optional feature** of `remoted`: it is only started when the manager's `<remote>` configuration block ([Remote_Config](Remote_Config.md)) defines a connection of type `syslog` with a `protocol` of `udp` or `tcp`. When enabled, it runs as a dedicated thread/loop inside the `remoted` process, parallel to the main secure-connection listener described in [remoted_secure_connection.md](remoted_secure_connection.md).

## Core Components

| Component | File | Description |
|---|---|---|
| `HandleSyslog()` | `src/remoted/syslog.c` | Main loop for the **UDP** syslog listener. Blocks on `recvfrom()`, extracts source IP, strips the PRI header, validates against allow/deny lists, and forwards to the queue. |
| `OS_IPNotAllowed()` (static, syslog.c) | `src/remoted/syslog.c` | IP filter check used by the UDP listener, backed by `logr.denyips` / `logr.allowips`. |
| `HandleSyslogTCP()` | `src/remoted/syslogtcp.c` | Main loop for the **TCP** syslog listener. Accepts connections, forks a child process per client, and manages an accounting loop over child PIDs. |
| `HandleClient()` (static, syslogtcp.c) | `src/remoted/syslogtcp.c` | Per-connection handler forked by `HandleSyslogTCP()`. Reads a stream of bytes into a growing buffer and delegates line-splitting/forwarding to `send_buffer()`. |
| `send_buffer()` | `src/remoted/syslogtcp.c` | Splits the raw TCP byte stream on `\n` boundaries, strips PRI headers per line, and sends each complete message to the queue via `SendMSG()`. |
| `w_get_pri_header_len()` (`STATIC`) | `src/remoted/syslogtcp.c` | Utility that computes the length of an optional `<PRI>` syslog header (RFC3164) so it can be skipped before forwarding the message body. |
| `OS_IPNotAllowed()` (static, syslogtcp.c) | `src/remoted/syslogtcp.c` | IP filter check used by the TCP listener (functionally identical to the UDP variant but operating on a different translation unit). |
| `sockaddr`, `sockaddr_in`, `sockaddr_in6`, `sockaddr_storage` | `src/remoted/syslog.c` | Standard BSD socket address structures used to receive and identify the source of incoming UDP datagrams. |

> Note: the module intentionally duplicates a small `OS_IPNotAllowed()` helper and IP handling logic between the UDP (`syslog.c`) and TCP (`syslogtcp.c`) implementations rather than sharing one function, since they evolved as separate protocol handlers within `remoted`.

## Architecture Overview

```mermaid
graph TB
    subgraph External_Sources["External Network Devices"]
        FW[Firewalls / Switches / Appliances]
    end

    subgraph Remoted_Daemon["remoted daemon"]
        subgraph Syslog_Listener["remoted_syslog_listener (this module)"]
            UDP[HandleSyslog - UDP loop]
            TCP[HandleSyslogTCP - TCP accept loop]
            CLIENT[HandleClient - per-connection fork]
            BUF[send_buffer - line splitter]
            PRI[w_get_pri_header_len]
            FILT1[OS_IPNotAllowed - UDP]
            FILT2[OS_IPNotAllowed - TCP]
        end
        SEC[remoted_secure_connection<br/>Wazuh agent protocol listener]
        STATE[remoted_state_metrics]
    end

    QUEUE[(queue/sockets/queue<br/>Local Message Queue)]
    ANALYSISD[analysisd]

    FW -- UDP:514/other --> UDP
    FW -- TCP:514/other --> TCP
    TCP --> CLIENT
    CLIENT --> BUF
    BUF --> PRI
    UDP --> FILT1
    CLIENT --> FILT2
    FILT1 -- allowed --> QUEUE
    FILT2 -- allowed --> QUEUE
    UDP -. denied .-> DROP1[Dropped + Warning Logged]
    CLIENT -. denied .-> DROP2[Connection Closed]
    QUEUE --> ANALYSISD

    SEC -.shares process with.- Syslog_Listener
    Syslog_Listener -.does not update.- STATE
```

## Data Flow

### UDP Syslog Path (`HandleSyslog`)

```mermaid
sequenceDiagram
    participant Dev as External Device
    participant UDP as HandleSyslog (UDP loop)
    participant Filter as OS_IPNotAllowed
    participant Queue as StartMQ / SendMSG
    participant Analysis as analysisd

    Note over UDP: Connects to DEFAULTQUEUE at startup<br/>(infinite retry)
    Dev->>UDP: UDP datagram (syslog message)
    UDP->>UDP: recvfrom() blocks until data arrives
    UDP->>UDP: Null-terminate & strip trailing newline
    UDP->>UDP: Extract srcip from sockaddr_in/in6
    UDP->>UDP: Strip optional "<PRI>" header
    UDP->>Filter: OS_IPNotAllowed(srcip)
    alt IP denied
        Filter-->>UDP: 1 (denied)
        UDP->>UDP: mwarn(DENYIP_WARN) & continue loop
    else IP allowed
        Filter-->>UDP: 0 (allowed)
        UDP->>Queue: SendMSG(m_queue, buffer, srcip, SYSLOG_MQ)
        alt Send fails
            Queue-->>UDP: error
            UDP->>Queue: StartMQ() reconnect (infinite attempts)
            UDP->>Queue: retry SendMSG()
        else Send succeeds
            Queue->>Analysis: Message delivered via local socket
        end
    end
```

### TCP Syslog Path (`HandleSyslogTCP` / `HandleClient` / `send_buffer`)

```mermaid
sequenceDiagram
    participant Dev as External Device
    participant TCP as HandleSyslogTCP (accept loop)
    participant Child as Forked Child (HandleClient)
    participant Buf as send_buffer
    participant Queue as SendMSG
    participant Analysis as analysisd

    Note over TCP: Connects to DEFAULTQUEUE at startup
    loop Accept loop
        TCP->>TCP: Reap finished children (waitpid, WNOHANG)
        Dev->>TCP: TCP connect()
        TCP->>TCP: OS_AcceptTCP() -> client_socket, srcip
        TCP->>TCP: OS_IPNotAllowed(srcip)
        alt IP denied
            TCP->>TCP: close(client_socket) & continue
        else IP allowed
            TCP->>Child: fork()
            Child->>Child: CreatePID(), init buffer
            loop Read stream
                Dev->>Child: TCP data (recv)
                Child->>Buf: send_buffer(&socket_buff, srcip)
                Buf->>Buf: Find each "\n" delimited message
                Buf->>Buf: w_get_pri_header_len() strips <PRI>
                Buf->>Queue: SendMSG per complete line
                Queue->>Analysis: Message delivered via local socket
                Buf->>Buf: Shift remaining partial data to buffer start
            end
            Dev--xChild: connection closed / recv()<=0
            Child->>Child: close(client_socket), DeletePID(), exit(0)
        end
    end
```

## Component Interaction

```mermaid
classDiagram
    class HandleSyslog {
        +void HandleSyslog()
        -int OS_IPNotAllowed(srcip)
    }
    class HandleSyslogTCP {
        +void HandleSyslogTCP()
        -void HandleClient(client_socket, srcip)
        -int OS_IPNotAllowed(srcip)
    }
    class send_buffer {
        +void send_buffer(sockbuffer_t*, srcip)
    }
    class w_get_pri_header_len {
        +size_t w_get_pri_header_len(syslog_msg)
    }
    class sockbuffer_t {
        char* data
        int data_len
    }
    class RemotedGlobals {
        logr.denyips
        logr.allowips
        logr.m_queue
        logr.udp_sock
        logr.tcp_sock
    }

    HandleSyslogTCP --> send_buffer : delegates line parsing
    send_buffer --> w_get_pri_header_len : strips PRI header per line
    HandleSyslogTCP --> sockbuffer_t : maintains per-connection buffer
    HandleSyslog --> RemotedGlobals : reads udp_sock, denyips/allowips
    HandleSyslogTCP --> RemotedGlobals : reads tcp_sock, denyips/allowips
    send_buffer --> RemotedGlobals : uses m_queue for SendMSG
```

## Key Behaviors & Design Notes

1. **Two independent transports, two independent loops.** UDP is handled inline in a single-process loop (`HandleSyslog`), while TCP uses the classic **fork-per-connection** model (`HandleSyslogTCP` + `HandleClient`), consistent with legacy Wazuh/OSSEC networking code found throughout [remoted_networking.md](remoted_networking.md).
2. **IP allow/deny filtering** is applied identically in both transports using the `logr.denyips` / `logr.allowips` lists (populated from `remote-config` — see [Remote_Config](Remote_Config.md)). Deny takes precedence; if not explicitly denied, the IP must be present in `allowips` (when configured) to be accepted.
3. **PRI header stripping.** Syslog messages may optionally begin with a `<PRI>` header per RFC3164. Both listeners detect and skip this header before handing the message to `SendMSG()`, ensuring the stored event body doesn't carry redundant framing information. The TCP path exposes this as a testable static function `w_get_pri_header_len()` (visible under `STATIC` macro for unit testing — see `test_syslogtcp_remoted` in [Unit_Tests_-_Remoted.md](Unit_Tests_-_Remoted.md)).
4. **Reliable delivery to the local queue.** Both paths call `SendMSG()` against `logr.m_queue`, and on failure will attempt an **infinite-retry reconnect** via `StartMQ(DEFAULTQUEUE, WRITE, INFINITE_OPENQ_ATTEMPTS)`, mirroring the resiliency pattern used by other `remoted` senders (see `sendmsg.c` in [remoted_networking.md](remoted_networking.md)).
5. **TCP stream reassembly.** Because TCP is a byte stream, `send_buffer()` accumulates data in a `sockbuffer_t` buffer and only forwards complete `\n`-terminated messages, retaining any partial trailing data for the next `recv()` call.
6. **Child process lifecycle for TCP.** `HandleSyslogTCP()` reaps completed child processes on each loop iteration using non-blocking `waitpid(..., WNOHANG)`, preventing zombie process accumulation while still promptly accepting new connections.
7. **No dedicated metrics.** Unlike the main secure connection handler, this module does not update `remoted_state_t` counters (see [remoted_state_metrics.md](remoted_state_metrics.md)); syslog throughput is not separately tracked in `remoted`'s internal statistics.

## Dependencies

| Dependency | Where Documented | Used For |
|---|---|---|
| `logr` global config (denyips/allowips/sockets/m_queue) | [remoted_lifecycle.md](remoted_lifecycle.md) | Access to configured IP lists and active sockets |
| `SendMSG`, `StartMQ` | [shared_lib.md](shared_lib.md) (`src/shared/mq_op.c`) | Delivering messages to the local Wazuh queue |
| `OS_IPFoundList` | [shared_lib.md](shared_lib.md) (`src/shared/validate_op.c`) | Underlying IP list matching logic used by `OS_IPNotAllowed()` |
| `get_ipv4_string`, `get_ipv6_string`, `OS_AcceptTCP` | [os_net.md](os_net.md) (`src/os_net/os_net.c`) | Address formatting and TCP accept helper |
| `remote-config` (`<remote type="syslog">`) | [Remote_Config.md](Remote_Config.md) | Enables/configures this listener (protocol, allowed/denied IPs, port) |
| `remoted_state_metrics`, `remoted_secure_connection`, `remoted_networking` | Sibling `remoted` submodules | Peer subsystems running within the same daemon process |

## Where This Fits in the System

```mermaid
graph LR
    subgraph Agent_Manager_Native_Daemons["Agent & Manager Native Daemons (C)"]
        direction TB
        RM[remoted]
        subgraph RM_Children["remoted children"]
            LC[remoted_lifecycle]
            SC[remoted_secure_connection]
            GM[remoted_group_management]
            NET[remoted_networking]
            REQ[remoted_request_protocol]
            STM[remoted_state_metrics]
            SYS[remoted_syslog_listener<br/>THIS MODULE]
        end
        RM --> RM_Children
    end
    SYS --> QUEUE[(Local Queue)]
    QUEUE --> WMD[Wazuh Modules Daemon /<br/>analysisd pipeline]
```

The syslog listener is one of several sibling components that make up the `remoted` daemon. It has minimal coupling with the rest of `remoted` — sharing only the global `logr` configuration structure and the local message queue handle — making it a self-contained, easily testable network ingestion path for non-Wazuh syslog sources.

## Testing

Unit tests for this module live under `src/unit_tests/remoted/test_syslogtcp.c`, focused specifically on the PRI-header parsing utility `w_get_pri_header_len()` (see `test_syslogtcp_remoted` in [Unit_Tests_-_Remoted.md](Unit_Tests_-_Remoted.md)). Broader `remoted` behaviors (secure connections, group management, etc.) are covered by sibling test suites within the same unit test module.
