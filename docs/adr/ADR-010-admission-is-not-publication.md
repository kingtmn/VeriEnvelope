# ADR-010: Admission is a verification decision, not a publication state

## Status

Accepted. This does not rewrite earlier evidence packages.

## Context

`candidate` and `admitted` were both easy to read as “is this included?”. They answer different questions.

## Decision

`component.status` is the registry lifecycle. The values are `candidate` and `withdrawn`. `candidate` means the identity is recorded. It is not a verification result and not a recommendation. `withdrawn` means the object is no longer in that lifecycle.

`result.admission` is the verification policy decision. The values stay `admitted`, `insufficient`, and `withheld`. `admitted` means the current admission policy allows inclusion inside the declared envelope. It does not publish the object, certify it, or decide fitness for use.

The runner still does not write `component.status`.

## Consequences

A component file cannot use `status: admitted`. An evidence result may still contain `admission: admitted`. Those two records stay side by side, and they do not mean the same thing.
