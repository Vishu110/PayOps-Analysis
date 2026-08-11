# Master Data Business Rules

---

# 1. Project Context

## Purpose

Nimbus is a fictional global payment platform inspired by modern payment infrastructure providers such as Stripe.

The objective of this project is not to recreate Stripe's internal systems exactly, but to simulate a realistic payment ecosystem that mirrors how modern payment platforms operate. Every dataset, business rule, and operational scenario is designed to resemble real-world payment operations while remaining simple enough to understand and extend.

The project serves two primary purposes:

1. To develop a deep understanding of payment systems and payment operations.
2. To provide a realistic environment for building and practicing data analytics, reconciliation, operational investigations, fraud analysis, financial reporting, and automation.

The generated data is intentionally interconnected. Every customer, merchant, payment method, product, processor, and bank exists as part of a complete payment ecosystem rather than as independently generated records.

---

## Project Goals

The simulator is designed to model the operational responsibilities typically performed within a global payments organization.

The primary goals are:

- Simulate realistic end-to-end payment flows.
- Generate internally consistent payment data.
- Simulate operational failures and payment incidents.
- Practice payment reconciliation across multiple systems.
- Investigate payment failures using SQL.
- Build operational dashboards and monitoring systems.
- Automate repetitive payment operations.
- Develop AI-assisted operational workflows.
- Understand how engineering, finance, banking partners, and operations interact within a payment platform.

---

## Scope of Version 1

Version 1 focuses on the core card payment lifecycle.

Supported capabilities include:

- Customer management
- Merchant management
- Product catalog
- Payment processors
- Issuing banks
- Card payment methods
- Payment authorization
- Payment capture
- Settlement
- Refunds
- Reconciliation
- Operational monitoring

The simulator intentionally focuses on payment operations rather than frontend checkout experiences.

---

## Design Philosophy

The project follows five core principles.

### 1. Business First

Business rules are defined before implementation.

Every table, relationship, and simulation exists because it represents a real business process rather than a technical requirement.

### 2. Data Integrity

Every generated record must be logically connected to every other record.

Randomly generated data that violates business rules is not acceptable.

### 3. Realistic Operations

Operational incidents, reconciliation differences, processor outages, settlement delays, duplicate events, and payment failures are intentionally introduced to simulate real production environments.

### 4. Explainability

Every generated record should be explainable.

If a payment exists, it should be possible to explain:

- who made the payment,
- what they purchased,
- which merchant received the payment,
- which processor handled the payment,
- which issuing bank authorized it,
- and how the payment ultimately affected the financial ledger.

### 5. Extensibility

The simulator is designed to evolve incrementally.

Future versions may introduce additional payment methods, countries, processors, fraud detection, AI-driven automation, and more advanced operational scenarios without requiring major architectural changes.

---

## Guiding Principle

The simulator should always prioritize realism over randomness.

Every generated record should represent a believable business event that could reasonably occur within a modern global payments platform.



# 2. Business Model

## Overview

Nimbus is a payment infrastructure platform that enables businesses to securely accept electronic payments from customers across multiple countries.

Nimbus does not sell products or services directly to consumers. Instead, it provides the infrastructure that allows merchants to collect payments from their customers while coordinating with payment processors, card networks, and issuing banks.

Nimbus acts as the trusted intermediary between all participants involved in the payment ecosystem.

---

## Primary Business Entities

The Nimbus ecosystem consists of six primary participants.

### 1. End Customers

End customers are individuals who purchase products or services from merchants.

They initiate payment requests using one of their registered payment methods.

End customers do not have a direct commercial relationship with Nimbus. Their relationship is with the merchant from whom they are purchasing.

---

### 2. Merchants

Merchants are businesses that integrate with Nimbus to accept online payments.

Merchants use Nimbus to:

- Accept payments
- Receive settlements
- Process refunds
- Monitor payment performance
- Resolve payment disputes

Merchants are Nimbus's direct business customers.

---

### 3. Payment Processors

Payment processors provide the infrastructure required to transmit payment requests between Nimbus and the wider payment ecosystem.

Nimbus routes payment requests to one of its integrated processors based on business rules, merchant configuration, and processor availability.

---

### 4. Card Networks

Card networks facilitate communication between payment processors and issuing banks.

Version 1 supports:

- Visa
- Mastercard
- American Express

Card networks are represented within payment methods and routing logic but are not modelled as independent database tables in Version 1.

---

### 5. Issuing Banks

Issuing banks issue payment cards to customers.

Their responsibilities include:

- Authenticating cardholders
- Checking available funds
- Performing fraud checks
- Approving or declining payment authorizations

---

### 6. Nimbus Platform

Nimbus coordinates the complete payment lifecycle.

Its responsibilities include:

- Receiving payment requests
- Routing payments
- Recording financial events
- Performing reconciliation
- Monitoring operational health
- Coordinating settlements
- Supporting merchants during payment incidents

Nimbus never becomes the merchant of record.

Instead, it operates as the payment platform connecting every participant within the ecosystem.



# 3. Geography

## Overview

Nimbus operates across multiple countries to simulate a realistic global payment platform.

The supported countries have been intentionally selected to represent different regions, currencies, payment behaviors, and merchant ecosystems.

This enables the simulator to generate both domestic and cross-border payment scenarios while maintaining realistic business distributions.

---

## Geographic Expansion

Nimbus expanded gradually rather than launching globally.

Expansion Timeline:

| Year | Countries Added |
|------|------------------|
| 2021 | India |
| 2022 | United States, Singapore |
| 2023 | United Kingdom, Germany |
| 2024 | Australia, Canada |

This staged expansion produces a customer base that naturally reflects company growth over time.

---

## Supported Countries

| Country | ISO Code | Currency | Customer Distribution |
|----------|----------|----------|----------------------:|
| India | IN | INR | 40% |
| United States | US | USD | 25% |
| United Kingdom | GB | GBP | 10% |
| Germany | DE | EUR | 8% |
| Australia | AU | AUD | 7% |
| Singapore | SG | SGD | 5% |
| Canada | CA | CAD | 5% |

Total Customer Distribution = 100%

---

## Currency Rules

Every country has one default operating currency.

| Country | Currency |
|----------|-----------|
| India | INR |
| United States | USD |
| United Kingdom | GBP |
| Germany | EUR |
| Australia | AUD |
| Singapore | SGD |
| Canada | CAD |

Customers are assigned the default currency of their country.

Merchants are also assigned a default settlement currency based on their primary country of operation.

Future versions may support multi-currency settlement.

---

## Domestic Payments

Most transactions occur within the same country.

Approximately 85% of generated payments should be domestic.

Examples:

- Indian customer → Indian merchant
- US customer → US merchant
- German customer → German merchant

Domestic payments generally have:

- Higher authorization success rates
- Faster settlement
- Lower processing costs

---

## Cross-Border Payments

Approximately 15% of generated payments should be international.

Examples:

- Indian customer purchasing from Amazon US
- Canadian customer subscribing to Spotify
- Australian customer purchasing from Airbnb

Cross-border payments are intentionally included because they introduce more complex operational scenarios, including:

- Currency differences
- Longer settlement timelines
- Increased operational investigations
- Higher payment failure rates
- Greater reconciliation complexity




# 4. Customers

## Overview

Customers represent individuals who purchase products or services from merchants using the Nimbus payment platform.

Customers interact with Nimbus indirectly through merchants. They are not direct business customers of Nimbus but are the originators of payment requests.

Each customer represents a unique individual within the payment ecosystem.

---

## Customer Lifecycle

Every customer follows a simple lifecycle.

Registered

↓

Active Purchases

↓

Possible Risk Events

↓

Account Closure (optional)

Most customers remain active throughout the simulation.

Only a small percentage become blocked or closed due to fraud, compliance, or account inactivity.

---

## Customer Identity Rules

Every customer:

- Has one globally unique customer identifier.
- Has exactly one country of residence.
- Has one preferred operating currency.
- Has one risk segment.
- Has one account status.
- Has a registration date.
- May own between one and four payment methods.
- May purchase from multiple merchants.
- May perform domestic and international transactions.

---

## Customer Distribution

Approximately 50,000 customers will be generated.

Customer distribution by country:

| Country | Percentage |
|----------|-----------:|
| India | 40% |
| United States | 25% |
| United Kingdom | 10% |
| Germany | 8% |
| Australia | 7% |
| Singapore | 5% |
| Canada | 5% |

Customer distribution follows the overall geographic expansion strategy defined earlier.

---

## Risk Distribution

Risk levels represent the likelihood that future transactions require operational review.

| Risk Segment | Percentage |
|--------------|-----------:|
| LOW | 85% |
| MEDIUM | 12% |
| HIGH | 3% |

High-risk customers are expected to generate proportionally more payment failures, fraud investigations, chargebacks, and operational incidents during later simulation stages.

---

## Customer Status Distribution

| Status | Percentage |
|---------|-----------:|
| ACTIVE | 97% |
| BLOCKED | 2% |
| CLOSED | 1% |

Blocked customers cannot initiate new payment attempts.

Closed customers represent permanently closed accounts retained for historical reporting purposes.

---

## Customer Growth

Nimbus experiences gradual user growth over time.

Customer registration dates are intentionally skewed toward recent years.

| Year | Distribution |
|------|-------------:|
| 2021 | 5% |
| 2022 | 10% |
| 2023 | 18% |
| 2024 | 25% |
| 2025 | 27% |
| 2026 | 15% |

This distribution reflects increasing platform adoption rather than uniform customer acquisition.

---

## Currency Rules

Customers always use the default currency of their country.

Examples:

- India → INR
- United States → USD
- Germany → EUR

Version 1 does not support customers with multiple preferred currencies.

---

## Payment Method Rules

Every customer owns at least one payment method.

Payment method distribution:

| Number of Payment Methods | Percentage |
|--------------------------:|-----------:|
| 1 | 45% |
| 2 | 35% |
| 3 | 15% |
| 4 | 5% |

Each payment method belongs to exactly one issuing bank.

One payment method is designated as the customer's default payment method.

---

## Business Validation Rules

The following conditions must always be true.

- Customer IDs are unique.
- Email addresses are unique.
- Preferred currency matches the customer's country.
- Signup date cannot occur in the future.
- Closed customers cannot become active again.
- Every customer must own at least one payment method.
- Every payment method must belong to an existing customer.