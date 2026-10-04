# Webhooks

AtlasFlow supports outbound webhooks for event-driven integrations on eligible plans.

## Plan availability

Webhooks are available on:

- Growth
- Enterprise

## Common webhook use cases

Customers use webhooks to:

- react to workflow completion events
- trigger downstream processing when approvals change state
- synchronize exceptions into incident or ticketing systems
- reduce polling against the AtlasFlow API

## Supported event examples

Examples of webhook event categories include:

- workflow run started
- workflow run completed
- approval requested
- approval completed
- automation failed

The exact event catalog may evolve over time.

## Delivery security

Webhook requests are signed using a webhook signing secret configured for the endpoint.

Consumers should validate the signature before trusting the payload.

## Retry behavior

If AtlasFlow does not receive a successful acknowledgment, delivery is retried.

Standard retry behavior:

- up to **8 retry attempts**
- retry window of up to **24 hours**

## Idempotency guidance

Webhook consumers should be designed for idempotency.

Important notes:

- duplicate delivery is possible
- retries may arrive after a temporary outage clears
- consumers should use event identifiers or other deduplication logic where appropriate

## Common failure causes

Webhook delivery issues are often caused by:

- endpoint timeouts
- invalid TLS configuration
- signature validation failures on the receiver side
- destination systems that do not handle retries or duplicates correctly
