# corporate.lib.stripe Module Documentation

## Overview

The `corporate.lib.stripe` module is the core billing and payment processing system for Zulip's commercial offerings. It provides a comprehensive Stripe integration that handles subscription management, invoicing, payment processing, and billing operations for both Zulip Cloud (SaaS) and self-hosted deployments.

This module serves as the central hub for all billing-related functionality, managing customer subscriptions, processing payments, handling plan upgrades/downgrades, and coordinating with Stripe's payment infrastructure.

## Architecture

### Core Components

The module is built around several key architectural components:

#### 1. BillingSession Abstract Base Class
The `BillingSession` class provides a unified interface for billing operations across different entity types (realms, remote realms, and remote servers). It defines the contract for all billing-related operations and ensures consistent behavior across different deployment models.

#### 2. Concrete BillingSession Implementations
- **RealmBillingSession**: Handles billing for Zulip Cloud organizations (realms)
- **RemoteRealmBillingSession**: Manages billing for self-hosted Zulip servers with realm-level billing
- **RemoteServerBillingSession**: Handles server-level billing for legacy self-hosted deployments

#### 3. Stripe Integration Layer
The module provides comprehensive Stripe integration through:
- Customer management and payment method handling
- Invoice generation and processing
- Payment processing and error handling
- Webhook processing capabilities

#### 4. Plan Management System
Handles different subscription tiers and billing models:
- Cloud plans (Standard, Plus)
- Self-hosted plans (Basic, Business, Community, Legacy)
- Fixed-price plans and custom arrangements
- Complimentary access plans

## System Architecture

```mermaid
graph TB
    subgraph "Billing System Core"
        BS[BillingSession<br/>Abstract Base]
        RBS[RealmBillingSession]
        RRBS[RemoteRealmBillingSession]
        RSBS[RemoteServerBillingSession]
        
        BS --> RBS
        BS --> RRBS
        BS --> RSBS
    end
    
    subgraph "Stripe Integration"
        SC[Stripe Customer<br/>Management]
        SI[Stripe Invoice<br/>Processing]
        SP[Stripe Payment<br/>Processing]
        SM[Stripe Metadata<br/>Handling]
        
        BS --> SC
        BS --> SI
        BS --> SP
        BS --> SM
    end
    
    subgraph "Data Models"
        C[Customer]
        CP[CustomerPlan]
        LL[LicenseLedger]
        I[Invoice]
        S[Session]
        
        BS --> C
        BS --> CP
        BS --> LL
        BS --> I
        BS --> S
    end
    
    subgraph "External Systems"
        ZC[Zulip Cloud<br/>Realms]
        SH[Self-Hosted<br/>Servers]
        SS[Stripe API]
        
        RBS --> ZC
        RRBS --> SH
        RSBS --> SH
        SC --> SS
        SI --> SS
        SP --> SS
    end
```

## Data Flow Architecture

```mermaid
sequenceDiagram
    participant User
    participant BillingSession
    participant Stripe
    participant Database
    participant AuditLog
    
    User->>BillingSession: Initiate upgrade
    BillingSession->>Database: Get customer data
    BillingSession->>Stripe: Create customer
    Stripe-->>BillingSession: Customer ID
    BillingSession->>Database: Store customer
    BillingSession->>AuditLog: Log creation
    
    User->>BillingSession: Add payment method
    BillingSession->>Stripe: Create setup session
    Stripe-->>BillingSession: Session URL
    User->>Stripe: Complete setup
    Stripe-->>BillingSession: Webhook confirmation
    BillingSession->>Database: Update customer
    BillingSession->>AuditLog: Log update
    
    User->>BillingSession: Subscribe to plan
    BillingSession->>Database: Create plan
    BillingSession->>Stripe: Generate invoice
    Stripe-->>BillingSession: Invoice ID
    BillingSession->>Database: Store invoice
    BillingSession->>AuditLog: Log subscription
```

## Component Relationships

```mermaid
graph LR
    subgraph "Billing Entities"
        R[Realm]
        RR[RemoteRealm]
        RS[RemoteServer]
    end
    
    subgraph "Billing Sessions"
        RBS2[RealmBillingSession]
        RRBS2[RemoteRealmBillingSession]
        RSBS2[RemoteServerBillingSession]
    end
    
    subgraph "Core Models"
        C2[Customer]
        CP2[CustomerPlan]
        LL2[LicenseLedger]
    end
    
    subgraph "Stripe Models"
        S2[Session]
        I2[Invoice]
    end
    
    R -->|has| RBS2
    RR -->|has| RRBS2
    RS -->|has| RSBS2
    
    RBS2 -->|manages| C2
    RRBS2 -->|manages| C2
    RSBS2 -->|manages| C2
    
    C2 -->|has| CP2
    CP2 -->|tracks| LL2
    
    RBS2 -->|creates| S2
    RBS2 -->|generates| I2
```

## Key Features

### 1. Multi-Entity Billing Support
The module supports three distinct billing models:
- **Zulip Cloud Realms**: Traditional SaaS billing with per-seat pricing
- **Remote Realms**: Self-hosted deployments with realm-level billing
- **Remote Servers**: Legacy server-level billing for pre-8.0 installations

### 2. Flexible Plan Management
- Multiple subscription tiers (Standard, Plus, Basic, Business, Community)
- Annual and monthly billing cycles
- Automatic and manual license management
- Fixed-price plans and custom arrangements
- Complimentary access and sponsorship programs

### 3. Comprehensive Payment Processing
- Stripe payment method management
- Automatic and invoice-based billing
- Prorated charges and credits
- Discount and coupon support
- Failed payment handling and retry logic

### 4. License Management
- Automatic license tracking based on user counts
- Manual license adjustment capabilities
- Guest user pricing calculations
- License ledger maintenance and auditing

### 5. Audit and Compliance
- Comprehensive audit logging for all billing events
- Support for both local and remote audit logs
- Transaction history and change tracking
- Compliance reporting capabilities

## Process Flows

### Upgrade Process Flow

```mermaid
flowchart TD
    Start([User initiates upgrade])
    CheckPlan{Check existing plan}
    HasPlan["Has active plan?"]
    NoPlan["No active plan"]
    
    Start --> CheckPlan
    CheckPlan -->|Yes| HasPlan
    CheckPlan -->|No| NoPlan
    
    HasPlan --> ValidateUpgrade{Validate upgrade}
    ValidateUpgrade -->|Valid| CreateInvoice["Create Stripe invoice"]
    ValidateUpgrade -->|Invalid| ErrorUpgrade["Return error"]
    
    NoPlan --> CheckFreeTrial{Free trial available?}
    CheckFreeTrial -->|Yes| SetupFreeTrial["Setup free trial"]
    CheckFreeTrial -->|No| CreateInvoice
    
    SetupFreeTrial --> ProcessPayment["Process payment method"]
    CreateInvoice --> ProcessPayment
    
    ProcessPayment -->|Success| ActivatePlan["Activate plan"]
    ProcessPayment -->|Failed| HandleFailure["Handle payment failure"]
    
    ActivatePlan --> LogAudit["Write audit log"]
    HandleFailure --> LogFailure["Log failure"]
    
    LogAudit --> End([End])
    LogFailure --> End
    ErrorUpgrade --> End
```

### Invoice Processing Flow

```mermaid
flowchart TD
    Start([Invoice due date reached])
    CheckPlan{Check plan status}
    ActivePlan["Plan is active"]
    EndingPlan["Plan ending"]
    
    Start --> CheckPlan
    CheckPlan -->|Active| ActivePlan
    CheckPlan -->|Ending| EndingPlan
    
    ActivePlan --> CheckLicenses{Check license count}
    CheckLicenses -->|Changed| UpdateLicenses["Update license ledger"]
    CheckLicenses -->|Same| GenerateInvoice["Generate invoice"]
    
    EndingPlan --> ProcessDowngrade["Process downgrade"]
    ProcessDowngrade --> EndPlan["End plan"]
    
    UpdateLicenses --> GenerateInvoice
    GenerateInvoice --> ApplyDiscounts["Apply discounts"]
    ApplyDiscounts --> CreateStripeInvoice["Create Stripe invoice"]
    CreateStripeInvoice --> SendInvoice["Send/process invoice"]
    
    SendInvoice -->|Success| LogSuccess["Log success"]
    SendInvoice -->|Failed| LogFailure["Log failure"]
    
    LogSuccess --> UpdateNextDate["Update next invoice date"]
    LogFailure --> RetryLogic["Schedule retry"]
    
    UpdateNextDate --> End([End])
    RetryLogic --> End
    EndPlan --> End
```

## Integration Points

### Dependencies
- **corporate.models**: Customer, CustomerPlan, LicenseLedger, Invoice, Session models
- **zilencer.models**: RemoteRealm, RemoteZulipServer, RemoteRealmAuditLog, RemoteZulipServerAuditLog
- **zerver.models**: Realm, UserProfile, RealmAuditLog
- **stripe**: Official Stripe Python SDK for payment processing

### Related Modules
- **[corporate.models.customers](corporate.models.customers.md)**: Customer data management
- **[corporate.models.plans](corporate.models.plans.md)**: Plan and subscription models
- **[zilencer.models](zilencer.models.md)**: Remote server and realm management
- **[zerver.models.realms](zerver.models.realms.md)**: Zulip Cloud realm management

## Error Handling

The module implements comprehensive error handling with specific exception types:

- **BillingError**: General billing operation failures
- **StripeCardError**: Payment method issues
- **StripeConnectionError**: Stripe API connectivity problems
- **LicenseLimitError**: License count violations
- **UpgradeWithExistingPlanError**: Conflicting upgrade attempts
- **InvalidPlanUpgradeError**: Invalid plan transitions

All Stripe operations are wrapped with the `@catch_stripe_errors` decorator to ensure consistent error handling and logging.

## Security Considerations

### Payment Security
- All payment processing is handled through Stripe's PCI-compliant infrastructure
- No credit card data is stored locally
- Payment method updates use Stripe's secure tokenization

### Access Control
- Billing operations require appropriate user permissions
- Support staff actions are logged with acting user information
- Session-based authentication for billing operations

### Data Protection
- Customer data is encrypted in transit and at rest
- Audit logs maintain comprehensive change tracking
- Sensitive billing information is properly redacted in logs

## Performance Optimization

### Caching Strategy
- License counts are cached with 24-hour TTL to reduce database queries
- Stripe customer data is retrieved with minimal API calls
- Plan parameters are computed efficiently with proper date handling

### Database Optimization
- Transactions are used to ensure data consistency
- Selective field updates minimize database writes
- Proper indexing on billing-related models

### Background Processing
- Invoice generation can be processed asynchronously
- License ledger updates are batched when possible
- Audit log writes are optimized for bulk operations

## Monitoring and Observability

### Logging
- Comprehensive billing event logging to dedicated billing.log
- Stripe API interactions are logged for debugging
- Error conditions are logged with full context

### Metrics
- Plan upgrade/downgrade success rates
- Payment processing success/failure rates
- Invoice generation and payment timing
- License usage patterns and trends

### Alerting
- Failed payment notifications
- Billing system errors
- Unusual billing pattern detection
- Audit log anomalies

This module serves as the financial backbone of Zulip's commercial operations, providing a robust, scalable, and secure billing platform that supports the diverse needs of both cloud and self-hosted deployments.