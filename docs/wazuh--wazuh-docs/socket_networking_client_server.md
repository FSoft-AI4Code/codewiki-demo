# Socket Networking Client/Server Module

## Introduction

The **socket_networking_client_server** module provides high-level, event-driven Unix-domain-socket client and server abstractions used throughout Wazuh's C++ components (`shared_modules`, `wazuh_modules`, `syscheckd`, and various daemons that communicate over local sockets). It sits directly on top of the `socket_networking_primitives` module (which supplies `EpollWrapper` and `Socket`/`UnixAddress`) and exposes two templated, RAII-friendly classes:

- **`SocketClient<TSocket, TEpoll>`** (`socketClient.hpp`) — an asynchronous, auto-reconnecting client that connects to a Unix domain socket, and reads/writes framed messages using an internal epoll event loop running on a dedicated thread.
- **`SocketServer<TSocket, TEpoll>`** (`socketServer.hpp`) — an asynchronous Unix domain socket server that accepts multiple client connections, multiplexes I/O with epoll, and dispatches messages to a user-supplied callback.

Both classes are templated on the underlying socket and epoll implementations, allowing dependency injection for unit testing (mock sockets/epoll) while defaulting to the production `Socket<OSPrimitives>` and `EpollWrapper` implementations. This module is a foundational building block for higher-level communication components such as `SocketDBWrapper` (`socket_networking_db_wrapper`), the `router` module, `dbsync`, `rsync`, and `indexer_connector`.

This document describes the module's architecture, its internal control flow, and how it relates to neighboring modules in the `shared_utils` / `socket_networking` family.

---

## 1. Purpose and Core Functionality

| Component | Responsibility |
|---|---|
| `SocketClient` | Connects (with automatic exponential-backoff retry) to a Unix domain socket, runs a background thread with an epoll loop, sends/receives length-prefixed messages, and automatically reconnects on socket errors (`EPOLLERR`/`EPOLLHUP`). |
| `SocketServer` | Binds and listens on a Unix domain socket, accepts multiple concurrent client connections, tracks each client socket in a thread-safe map, and dispatches read/write events via epoll to caller-supplied callbacks. |

Both classes share the same design philosophy:

- **Non-blocking I/O** using `SOCK_NONBLOCK` sockets combined with `epoll` for readiness notification.
- **Self-pipe trick** (`m_stopFD` pipe pair) to cleanly and immediately break out of the blocking `epoll_wait` call when `stop()` is invoked, avoiding the need for polling timeouts.
- **Templated design** (`TSocket`, `TEpoll`) enabling compile-time substitution of mock objects for unit testing.
- **Message framing** delegated to the underlying `Socket` class (from `socket_networking_primitives`), which uses a pluggable `TCommunicationProtocol` (e.g., `SizeHeaderProtocol`) to build/parse header+body packets.
- **Thread safety** via mutexes/shared_mutex guarding socket access and client maps.

---

## 2. Architecture Overview

### 2.1 Component Relationships

```mermaid
graph TB
    subgraph socket_networking_client_server["socket_networking_client_server (this module)"]
        SC[SocketClient&lt;TSocket, TEpoll&gt;]
        SS[SocketServer&lt;TSocket, TEpoll&gt;]
    end

    subgraph socket_networking_primitives["socket_networking_primitives"]
        EW[EpollWrapper]
        SK[Socket&lt;T, TCommunicationProtocol&gt;]
        UA[UnixAddress]
        HDR[Header / SizeHeaderProtocol / NoHeaderProtocol]
        PKT[Packet]
    end

    subgraph socket_networking_helpers["socket_networking_helpers"]
        NH[networkHelper.h]
    end

    subgraph socket_networking_db_wrapper["socket_networking_db_wrapper"]
        SDW[SocketDBWrapper]
    end

    SC -->|uses| EW
    SC -->|uses| SK
    SC -->|builds address via| UA
    SS -->|uses| EW
    SS -->|uses| SK
    SS -->|builds address via| UA
    SK -->|delegates framing to| HDR
    SK -->|queues unsent data as| PKT

    SDW -->|composes/wraps| SC

    classDef current fill:#f9d77e,stroke:#333,stroke-width:2px;
    class SC,SS current;
```

### 2.2 Class Diagram

```mermaid
classDiagram
    class SocketClient~TSocket, TEpoll~ {
        -string m_socketPath
        -thread m_mainLoopThread
        -shared_ptr~TEpoll~ m_epoll
        -shared_ptr~TSocket~ m_socket
        -atomic~bool~ m_shouldStop
        -condition_variable_any m_cv
        -mutex m_mutex
        -shared_mutex m_socketMutex
        -int[2] m_stopFD
        +SocketClient(socketPath)
        +~SocketClient()
        +stop()
        +getSocketDescriptor() int
        +connect(onRead, onConnect, type)
        +handleConnect(type)
        +send(dataBody, sizeBody, dataHeader, sizeHeader)
        -sendPendingMessages()
    }

    class SocketServer~TSocket, TEpoll~ {
        -string m_socketPath
        -atomic~bool~ m_shouldStop
        -array~int,2~ m_stopFD
        -unique_ptr~TEpoll~ m_epoll
        -unique_ptr~TSocket~ m_listenSocket
        -unordered_map~int, shared_ptr~TSocket~~ m_clients
        -thread m_listenThread
        -mutex m_mutex
        +SocketServer(socketPath)
        +~SocketServer()
        +stop()
        +listen(onRead)
        +send(fd, dataBody, sizeBody, dataHeader, sizeHeader)
        -getClient(fd) shared_ptr~TSocket~
        -removeClient(fd)
        -addClient(fd, client)
        -sendPendingMessages(client)
        -processRead(client, onRead)
        -processEvent(event, eventFD, onRead)
    }

    class EpollWrapper {
        -int m_epollFD
        +wait(events, maxevents, timeout) int
        +addDescriptor(fd, events)
        +modifyDescriptor(fd, events)
        +deleteDescriptor(fd)
    }

    class Socket~T~ {
        -int m_sock
        -SocketStatus m_status
        -queue~Packet~ m_unsentPacketList
        +fileDescriptor() int
        +connect(connInfo, type)
        +listen(connectInfo)
        +accept() int
        +read(callback)
        +send(dataBody, sizeBody, dataHeader, sizeHeader)
        +sendUnsentMessages()
        +closeSocket()
    }

    class UnixAddress {
        -sockaddr_un m_unixAddr
        +address(path) UnixAddress
    }

    SocketClient --> EpollWrapper : m_epoll
    SocketClient --> Socket : m_socket
    SocketClient ..> UnixAddress : builds address
    SocketServer --> EpollWrapper : m_epoll
    SocketServer "1" --> "many" Socket : m_clients
    SocketServer ..> UnixAddress : builds address
```

---

## 3. `SocketClient` — Detailed Behavior

### 3.1 Construction and Lifecycle

- The constructor creates a self-pipe (`m_stopFD`) used exclusively to interrupt the blocking `epoll_wait` call during shutdown. The read end is registered with epoll using edge-triggered mode (`EPOLLET`).
- `connect(onRead, onConnect, type)` spawns the background thread (`m_mainLoopThread`) only once; subsequent calls are no-ops while the thread is alive.
- `stop()` sets `m_shouldStop`, writes a dummy byte to the stop pipe to wake up `epoll_wait`, notifies the condition variable (in case a reconnect backoff is in progress), and joins the thread.

### 3.2 Connection & Reconnection Logic (`handleConnect`)

`handleConnect` implements an **exponential backoff retry** (capped at 30 seconds) loop:

1. Build a `UnixAddress` from `m_socketPath`.
2. Attempt `m_socket->connect(...)`; on success, register the socket file descriptor with epoll for `EPOLLIN | EPOLLOUT`.
3. On failure, wait on a condition variable for `delay` seconds (doubling each iteration, capped at `MAX_DELAY = 30`), or return early if `stop()` was requested.

This same method is re-invoked whenever the main loop detects `EPOLLERR`/`EPOLLHUP` on the socket, providing automatic reconnection.

### 3.3 Main Event Loop (`connect`)

```mermaid
sequenceDiagram
    participant Caller
    participant SocketClient
    participant Epoll as EpollWrapper
    participant Sock as Socket
    participant Server as Remote Unix Socket

    Caller->>SocketClient: connect(onRead, onConnect, type)
    SocketClient->>SocketClient: spawn m_mainLoopThread
    SocketClient->>SocketClient: handleConnect(type)
    SocketClient->>Sock: connect(unixAddress)
    Sock->>Server: connect()
    SocketClient->>Epoll: addDescriptor(fd, EPOLLIN|EPOLLOUT)

    loop while !m_shouldStop
        SocketClient->>Epoll: wait(events, -1)
        Epoll-->>SocketClient: ready events
        alt stopFD triggered
            SocketClient->>SocketClient: drain pipe, break
        else EPOLLERR/EPOLLHUP
            SocketClient->>SocketClient: handleConnect() [reconnect]
        else EPOLLOUT
            SocketClient->>Caller: onConnect() [only right after (re)connect]
            SocketClient->>Sock: sendUnsentMessages()
            Sock->>Server: flush queued Packets
            SocketClient->>Epoll: modifyDescriptor(fd, EPOLLIN)
        else EPOLLIN
            SocketClient->>Sock: read(callback)
            Sock-->>SocketClient: onRead(body, bodySize, header, headerSize)
            SocketClient->>Caller: onRead(...)
        end
    end
```

### 3.4 Sending Data

`send(dataBody, sizeBody, dataHeader, sizeHeader)`:
- Acquires a **shared** lock on `m_socketMutex` (allowing concurrent sends but exclusive access during reconnect).
- Delegates to `Socket::send`, which attempts an immediate `send()` syscall; unsent bytes are queued as a `Packet` (from `socket_networking_primitives`) for later transmission.
- On failure, re-arms the epoll descriptor for `EPOLLIN | EPOLLOUT` so the event loop retries via `sendPendingMessages()`.

---

## 4. `SocketServer` — Detailed Behavior

### 4.1 Construction and Lifecycle

- Similar self-pipe pattern as `SocketClient` for graceful, immediate shutdown.
- `listen(onRead)` removes any stale socket file, builds the bind address using `UnixAddress`, calls `Socket::listen` (which creates the file, sets permissions `0666`, and starts listening with `SOMAXCONN` backlog), registers the listening socket with epoll for `EPOLLIN`, and starts the background accept/dispatch thread.
- `stop()` signals the thread to exit, deletes the listening descriptor from epoll, and closes the socket. The destructor also removes the socket file from disk (`std::filesystem::remove_all`).

### 4.2 Client Management

Clients are tracked in `std::unordered_map<int, shared_ptr<TSocket>> m_clients`, guarded by `m_mutex`:

- `addClient(fd, socket)` — called upon `accept()`.
- `getClient(fd)` — thread-safe lookup used by the event dispatcher and by `send()`.
- `removeClient(fd)` — called when `EPOLLERR`/`EPOLLHUP` is detected for a client descriptor.

### 4.3 Main Event Loop (`listen`)

```mermaid
sequenceDiagram
    participant Caller
    participant SocketServer
    participant Epoll as EpollWrapper
    participant ListenSock as Listening Socket
    participant ClientSock as Client Socket
    participant Client as Remote Client

    Caller->>SocketServer: listen(onRead)
    SocketServer->>ListenSock: listen(unixAddress)
    SocketServer->>Epoll: addDescriptor(listenFD, EPOLLIN)
    SocketServer->>SocketServer: spawn m_listenThread

    loop while !m_shouldStop
        SocketServer->>Epoll: wait(events, -1)
        Epoll-->>SocketServer: ready events
        alt event on listenFD
            SocketServer->>ListenSock: accept()
            ListenSock-->>SocketServer: new client fd
            SocketServer->>SocketServer: addClient(fd, new Socket)
            SocketServer->>Epoll: addDescriptor(fd, EPOLLIN)
        else event on stopFD
            SocketServer->>SocketServer: drain pipe, break
        else event on client fd
            SocketServer->>SocketServer: processEvent(event, fd, onRead)
            alt EPOLLOUT
                SocketServer->>ClientSock: sendUnsentMessages()
                SocketServer->>Epoll: modifyDescriptor(fd, EPOLLIN)
            end
            alt EPOLLIN
                SocketServer->>ClientSock: read(onRead)
                ClientSock-->>SocketServer: onRead(fd, body, bodySize, header, headerSize)
                SocketServer->>Caller: onRead(...)
            end
            alt EPOLLERR/EPOLLHUP
                SocketServer->>SocketServer: removeClient(fd)
            end
        end
        Note over SocketServer: dynamically grows events vector if EVENTS_LIMIT exceeded
    end
```

### 4.4 Sending Data to a Specific Client

`send(fd, dataBody, sizeBody, dataHeader, sizeHeader)`:
- Looks up the client by `fd`; throws `std::out_of_range` if not found.
- Delegates to `Socket::send`; on failure, re-registers the descriptor for `EPOLLIN | EPOLLOUT` to retry sending once writable.

---

## 5. Data Flow: End-to-End Message Exchange

```mermaid
flowchart LR
    subgraph Client Process
        A[Application Code] -->|send data| B[SocketClient.send]
        B --> C[Socket.send / queue Packet]
        C -->|EPOLLOUT ready| D[sendPendingMessages]
    end

    subgraph "Unix Domain Socket (filesystem path)"
        E((socket file))
    end

    subgraph Server Process
        F[SocketServer.listen loop] -->|EPOLLIN| G[Socket.read]
        G -->|parses header+body via TCommunicationProtocol| H[onRead callback]
        H --> I[Server Application Logic]
        I -->|SocketServer.send fd, data| J[Socket.send to client fd]
    end

    D -.->|write syscall| E
    E -.->|accept / recv| F
    J -.->|write syscall| E
    E -.->|recv| B2[SocketClient read via EPOLLIN]
    B2 --> K[onRead callback in client]
```

---

## 6. Relationship to Other Modules

| Related Module | Relationship |
|---|---|
| [socket_networking_primitives](socket_networking_primitives.md) | Supplies `EpollWrapper`, `Socket<T, TCommunicationProtocol>`, `UnixAddress`, `Header`/`SizeHeaderProtocol`/`NoHeaderProtocol`, and `Packet` — the low-level primitives that `SocketClient`/`SocketServer` are built upon. |
| [socket_networking_db_wrapper](socket_networking_db_wrapper.md) | `SocketDBWrapper` composes a `SocketClient<Socket<OSPrimitives, SizeHeaderProtocol>, EpollWrapper>` internally to talk to Wazuh DB (`wazuh-db` socket), demonstrating a typical consumer of this module. |
| [socket_networking_helpers](socket_networking_helpers.md) | Provides lower-level network helper utilities (e.g., `networkHelper.h`) that may be used alongside socket communication for non-Unix-domain use cases. |
| [framework_core_communication_sockets](framework_core_communication.md) | The Python/C framework layer (`wazuh_socket.py`, `wazuh_queue.py`) implements analogous client/server socket patterns for the Python-based API and framework, serving a similar purpose at a different layer of the stack (JSON-based Wazuh socket protocol vs. this module's raw framed binary protocol). |
| [engine_httpsrv](Wazuh_Engine_Core_(C++).md) / [Router](Wazuh_Engine_Core_(C++).md) | Higher-level engine components (e.g., the Router's `udgramsrv`, `router.cpp`) build on similar epoll-based networking patterns for datagram and pub/sub communication, though they use different primitives (`iqueue`, `udsrv.cpp`). |
| [dbsync](Shared_Modules_Infrastructure_(C++).md), [rsync](Shared_Modules_Infrastructure_(C++).md), [indexer_connector](Shared_Modules_Infrastructure_(C++).md) | These shared modules commonly rely on socket-based IPC; `SocketClient`/`SocketServer` (or `SocketDBWrapper`, built on top of them) are the standard mechanism for such communication within the `shared_modules` C++ codebase. |

---

## 7. Design Notes & Testability

- **Template parameterization** (`TSocket`, `TEpoll`) is the primary testability mechanism: unit tests can substitute mock socket/epoll implementations (see `OSPrimitives`/`OsPrimitivesMac` abstractions and related wrapper interfaces in `socket_networking_primitives`) to simulate connection failures, partial reads/writes, and epoll event sequences without real OS sockets.
- **Self-pipe trick**: Both classes use a pipe (`m_stopFD`) registered in the epoll set with `EPOLLET` (edge-triggered) to guarantee immediate wake-up on `stop()`, avoiding polling delays inherent to a timeout-based `epoll_wait`.
- **Locking strategy**:
  - `SocketClient` uses a `shared_mutex` (`m_socketMutex`) to allow multiple concurrent `send()` calls (shared lock) while reserving exclusive access during reconnect (`handleConnect`) and pending-message flush (`sendPendingMessages`).
  - `SocketServer` uses a plain `mutex` guarding the `m_clients` map, since client socket objects themselves are not expected to be accessed concurrently by multiple sender threads in the same way.
- **Error handling**: Both classes swallow most I/O exceptions inside the event loop (logging to `stderr`) and rely on `EPOLLERR`/`EPOLLHUP` for terminal socket-state detection — for the client, this triggers reconnection; for the server, it triggers client removal.
- **Framing agnostic**: Neither class parses message framing directly — this responsibility is delegated to the templated `Socket<T, TCommunicationProtocol>` from `socket_networking_primitives`, allowing the same client/server logic to support different wire protocols (e.g., `SizeHeaderProtocol`, `NoHeaderProtocol`).

---

## 8. Typical Usage Pattern

```cpp
// Server side
SocketServer<Socket<OSPrimitives>, EpollWrapper> server("/var/ossec/queue/my.sock");
server.listen([](int fd, const char* body, uint32_t bodySize, const char* header, uint32_t headerSize) {
    // process the client's message
    // ... respond if needed:
    // server.send(fd, responseData, responseSize);
});
// ... later
server.stop();

// Client side
SocketClient<Socket<OSPrimitives>, EpollWrapper> client("/var/ossec/queue/my.sock");
client.connect(
    [](const char* body, uint32_t bodySize, const char* header, uint32_t headerSize) {
        // handle incoming data
    },
    []() {
        // called right after a (re)connection succeeds; good place to send initial handshake
    }
);
client.send(requestData, requestSize);
// ... later
client.stop();
```

This pattern is exemplified in production code by `SocketDBWrapper::init()`, which wraps a `SocketClient` to implement request/response semantics against the Wazuh DB daemon.
