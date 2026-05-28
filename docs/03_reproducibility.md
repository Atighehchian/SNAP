# Reproducibility

The generator uses deterministic seeds so that generated instances can be reproduced.

For profile `snap_s`, instance index `1`, and base seed `20260508`, the instance seed is:

```text
20260508 + 1 × 1009 = 20261517
```

The exact seed is stored in each instance's `metadata.json`.

Recommended manuscript language:

> We generated SNAP benchmark instances using a SNAP-specific Taillard-inspired generation protocol. Each instance family was controlled by problem size and difficulty parameters, and each instance was produced using a deterministic seed protocol. A planted feasible schedule and complexity metadata were stored with every instance.
