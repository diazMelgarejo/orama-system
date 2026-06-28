---
name: local-inference
description: >-
  REDIRECT → perpetua-hardware → hardware-affinity-gate. Local-inference
  endpoint selection and model routing are governed by the hardware affinity
  policy. No procedure lives here.
version: 1.0.0
license: Apache 2.0
parent_skill: orama-system
---

# Local Inference

> **Redirected:** Local-inference routing (LM Studio, Ollama, GGUF/MLX affinity) is
> defined in [`../hardware-affinity-gate/SKILL.md`](../hardware-affinity-gate/SKILL.md)
> (via [`../perpetua-hardware/SKILL.md`](../perpetua-hardware/SKILL.md)).
>
> For LAN endpoint naming conventions (localhost vs cross-machine `$WIN_IP`/`$MAC_IP`),
> see [`../hermes-harness/references/lan-endpoint-contract.md`](../hermes-harness/references/lan-endpoint-contract.md).
>
> This stub exists so links to `local-inference` resolve; load
> `hardware-affinity-gate` to act.
