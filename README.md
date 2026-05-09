<div align="center">

  

  # <img src="assets/images/diffuagent_icon.png" alt="DiffuAgent Icon" width="30"> DiffuAgent

  ### The Bitter Lesson of Diffusion Language Models for Agentic Workflows: A Comprehensive Reality Check

  **Qingyu Lu<sup>1,3</sup>, Liang Ding<sup>2</sup>, Kanjian Zhang<sup>2</sup>, Jinxia Zhang<sup>1</sup>, Dacheng Tao<sup>3</sup>**

  <sup>1</sup>Southeast University, China &nbsp;|&nbsp;
  <sup>2</sup>Alibaba &nbsp;|&nbsp;
  <sup>3</sup>Nanyang Technological University, Singapore

  [![Paper](https://img.shields.io/badge/PDF-Paper-red)](https://arxiv.org/pdf/2601.12979)
  [![Code](https://img.shields.io/badge/GitHub-Pages-blue)](https://coldmist-lu.github.io/DiffuAgent/)

</div>

## TL;DR

- **Efficiency ≠ Agentic Effectiveness.** Despite low latency, diffusion-based LLMs (**dLLMs**) fail to serve as reliable agent backbones in both long-horizon **embodied** tasks and precision-critical **tool-calling** scenarios.

- **Systematic Agentic Failures.** dLLMs exhibit characteristic failure modes, including retry loops under temporal feedback and loss of symbolic precision (e.g., malformed JSON) under diffusion noise.

- **DiffuAgent Framework.** We introduce **DiffuAgent**, a unified and modular framework for evaluating dLLMs across embodied and tool-calling agentic workflows.

- **Where dLLMs Work.** dLLMs remain effective in non-causal auxiliary roles (e.g., memory summarization and tool selection), but require causal and logically grounded mechanisms to function as full agent backbones.

## Failure Cases of dLLMs in Agentic Workflows

<p align="center">
  <img src="assets/images/dllm_failure_mode.png" alt="DLLM Failure Modes" width="80%">
</p>

- **In Embodied settings**, dLLMs suffer repeated attempts (**retry loops**), failing to branch under temporal feedback.
- **In Tool-Calling settings**, dLLMs fail to maintain **symbolic precision** (e.g., strict JSON schemas) under diffusion noise.

## Failure of dLLMs as Agent Backbones

<p align="center">
  <img src="assets/images/failure_tables.png" alt="Failure Tables" width="80%">
</p>

We compare dLLMs and autoregressive LLMs on embodied (AgentBoard) and tool-calling (BFCL) benchmarks.
The results show that dLLMs lag behind on both success/progress and tool-calling accuracy.

## Systematic Failure Modes of dLLMs

<p align="center">
  <img src="assets/images/failure_figs.png" alt="Failure Analysis" width="100%">
</p>

**(a) Failure of Replan for embodied agents**: dLLMs exhibit significantly more frequent retry loops than LLMs.

**(b) Failure of Precision for tool-calling agents**: dLLMs are more prone to produce malformed JSON schemas.

**(c) Performance-Efficiency Trade-offs**: despite higher inference efficiency, dLLMs do not guarantee comparable agentic performance to autoregressive LLMs.

## DiffuAgent: Framework on Analyzing Agentic Behaviors in dLLMs

<p align="center">
  <img src="assets/images/diffuagent.png" alt="DiffuAgent Framework" width="100%">
</p>

To better understand the agentic potential of dLLMs, we introduce DiffuAgent, a novel evaluation framework that treats dLLMs as plug-and-play cognitive modules for augmenting LLM agents.

### Framework Components

- **For embodied agents**, we introduce a memory-augmented module for history compression and an early-exit verifier for global trajectory checking.

- **For tool-calling agents**, we include a tool selector over the library of available tools, and a JSON format editor.

### Quick Start

For detailed installation and setup instructions:
- **AgentBoard**: [`installation.md`](DiffuAgent/Agentboard/installation.md) | [`Original Repo`](https://github.com/hkust-nlp/AgentBoard)
- **BFCL**: [`installation.md`](DiffuAgent/BFCL/installation.md) | [`Original Repo`](https://github.com/ShishirPatil/gorilla/blob/main/berkeley-function-call-leaderboard/)

> **Note:** Please refer to the original repositories for detailed environment requirements.

> **Note:** Our BFCL experiments have been extended to v4. To reproduce v3 experiments, please use the v3 codebase.

> **Note:** We used Claude Code for automatic code optimization, which passed preliminary testing. If you encounter any issues during use, please contact us.

## Local BFCL Reproduction Notes

This checkout keeps BFCL work in a separate nested Gorilla repository rather
than in the top-level DiffuAgent git history:

```text
DiffuAgent/
└── unified_envs/
    └── gorilla/                         # separate git repo
        └── berkeley-function-call-leaderboard/
```

The reproducible BFCL backbone setup is maintained on the fork branch below:

```bash
cd unified_envs/gorilla
git remote -v
# origin   git@github.com:martellato51/gorilla.git
# upstream https://github.com/ShishirPatil/gorilla

git checkout diffuagent-bfcl
```

That branch adds BFCL v4 handlers for:

- `backbone/qwen3-8b`: Qwen3-8B served through vLLM's OpenAI-compatible API.
- `backbone/llada`: LLaDA-8B-Instruct loaded locally through Fast-dLLM v1.

The main entry documents are:

- `unified_envs/gorilla/berkeley-function-call-leaderboard/installation.md`
- `unified_envs/gorilla/berkeley-function-call-leaderboard/README_BFCL_BACKBONE.md`
- `unified_envs/gorilla/berkeley-function-call-leaderboard/bfcl_eval/model_handler/api_inference/diffuagent/ENV_CONFIG.md`

On this server, the latest successful jobs are launched from
`/data/home/martellato41/research/run_bfcl_*.job` and use the shared `qwen3`
and `llada8b` conda environments. The Gorilla fork also contains portable
Slurm templates under `berkeley-function-call-leaderboard/jobs/`; those are the
starting point for bringing the setup up on another server.

If VS Code shows "Publish Branch" for the top-level `DiffuAgent` checkout, that
usually refers to the local top-level branch, not the nested Gorilla branch.
Check both repositories separately:

```bash
git status --branch --short
git -C unified_envs/gorilla status --branch --short
```

## Analysis of Agentic Behaviors in dLLMs

### Memory Augmentation

<p align="center">
  <img src="assets/images/analysis_memory.png" alt="Memory Analysis" width="70%">
</p>

**dLLMs are competitive memory modules** for memory-augmented agents.

### Early Exit Verification

<p align="center">
  <img src="assets/images/analysis_earlyexit.png" alt="Early Exit Analysis" width="40%">
</p>

LLM Verifiers tend to trigger premature early exits, whereas **dLLMs terminate more reliably**.

### Tool-Calling Analysis

<p align="center">
  <img src="assets/images/analysis_tool.png" alt="Tool Calling Analysis" width="80%">
</p>

dLLMs are **effective tool selectors** but **struggle as tool-call editors**.

## Citation

```bibtex
@article{lu2026diffuagent,
  title   = {The Bitter Lesson of Diffusion Language Models for Agentic Workflows: A Comprehensive Reality Check},
  author  = {Lu, Qingyu and Ding, Liang and Zhang, Kanjian and Zhang, Jinxia and Tao, Dacheng},
  journal = {arXiv preprint},
  year    = {2026},
  url     = {https://arxiv.org/pdf/2601.12979}
}
```

<div align="center">

  © 2026 DiffuAgent

</div>
