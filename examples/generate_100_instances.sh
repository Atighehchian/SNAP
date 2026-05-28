#!/usr/bin/env bash
# Generate the recommended 100-instance mixed benchmark set.
PYTHONPATH=src python scripts/generate_100_mixed_benchmark_instances.py --output instances_mixed_100 --seed 20260508
