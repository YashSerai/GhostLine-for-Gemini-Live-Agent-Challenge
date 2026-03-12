# Shared Contracts

This directory contains the Prompt 3 shared type and constant skeleton for Ghostline.

## Layout

- `contracts/product_constants.json`: language-neutral reference data for the core labels
- `typescript/productConstants.ts`: TypeScript constants and union types for frontend-side use
- `python/product_constants.py`: Python constants and type aliases for backend-side use

## Covered Labels

These files intentionally define only the product constants requested in Prompt 3:

- task IDs `T1` through `T15`
- task tiers `1`, `2`, `3`
- task role categories `containment`, `diagnostic`, `flavor`
- path modes `threshold`, `tabletop`, `low_visibility`
- verification result statuses `confirmed`, `unconfirmed`, `user_confirmed_only`
- session states
- case report verdicts `secured`, `partial`, `inconclusive`
- UI status labels `speaking`, `listening`, `interrupted`

## Session State Note

The product doc lists several states in prose using spaces such as `call connected` and `camera request`.
This shared contract uses snake_case machine labels such as `call_connected` and `camera_request` so client and server can reference exact values consistently.

No product logic lives here yet.
