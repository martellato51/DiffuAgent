# DiffuAgent BFCL 재현용 정리

이 브랜치는 원본 DiffuAgent 설명 문서가 아니라, 현재 서버에서 만든 BFCL 재현 세팅만 기록합니다. 목적은 다른 서버에서 지금 서버의 핵심 폴더 구조와 코드를 다시 받아서 Qwen3-8B와 LLaDA-8B BFCL backbone 평가를 재현하는 것입니다.

## 저장소 구조

중요한 코드는 top-level `DiffuAgent` repo 안에 직접 들어 있지 않고, 아래 nested Gorilla repo에 있습니다.

```text
DiffuAgent/
└── unified_envs/
    └── gorilla/                         # git submodule
        └── berkeley-function-call-leaderboard/
```

`unified_envs/gorilla`는 `martellato51/gorilla` fork의 `diffuagent-bfcl` 브랜치를 가리킵니다. 이 브랜치에 BFCL v4 기반 DiffuAgent backbone 평가 코드가 들어 있습니다.

## 다른 서버에서 받는 방법

submodule까지 같이 받습니다.

```bash
git clone --branch my-change --recurse-submodules git@github.com:martellato51/DiffuAgent.git
cd DiffuAgent
```

이미 clone한 뒤라면:

```bash
git submodule update --init --recursive
```

확인:

```bash
git status --branch --short
git -C unified_envs/gorilla status --branch --short
```

기대 상태:

```text
DiffuAgent: my-change
unified_envs/gorilla: diffuagent-bfcl
```

## 포함된 BFCL 내용

Gorilla submodule 안의 주요 파일:

```text
unified_envs/gorilla/berkeley-function-call-leaderboard/
├── README_BFCL_BACKBONE.md
├── installation.md
├── register_backbone.py
├── run_backbone_eval.sh
├── jobs/
│   ├── setup_bfcl_env.sbatch
│   └── run_backbone_eval.sbatch
├── bfcl_eval/
│   ├── build_handlers_backbone.py
│   └── model_handler/api_inference/diffuagent/
│       ├── handlers.py
│       ├── handlers_backbone.py
│       └── ENV_CONFIG.md
└── experiments/
    └── think_parallel/
```

등록되는 backbone 모델은 두 개입니다.

- `backbone/qwen3-8b`: Qwen3-8B를 vLLM OpenAI-compatible server로 띄워 BFCL 평가.
- `backbone/llada`: LLaDA-8B-Instruct를 Fast-dLLM v1 코드로 Python 프로세스 안에서 직접 로드해 BFCL 평가.

## 필요한 외부 폴더

repo에 포함되지 않는 모델 snapshot과 외부 checkout은 서버별로 준비해야 합니다.

```text
research/
├── DiffuAgent/
├── Fast-dLLM/
│   └── v1/llada/
└── model/
    ├── Qwen3-8B/
    └── LLaDA-8B-Instruct/
```

환경 변수로 경로를 바꿀 수 있습니다.

```bash
export RESEARCH_ROOT=/path/to/research
export BFCL_ROOT=$RESEARCH_ROOT/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard
export QWEN_MODEL_PATH=$RESEARCH_ROOT/model/Qwen3-8B
export LLADA_MODEL_PATH=$RESEARCH_ROOT/model/LLaDA-8B-Instruct
export FAST_DLLM_LLADA_PATH=$RESEARCH_ROOT/Fast-dLLM/v1/llada
```

## 설치와 실행

portable Slurm template은 Gorilla submodule 안에 있습니다.

```bash
cd unified_envs/gorilla/berkeley-function-call-leaderboard
sbatch jobs/setup_bfcl_env.sbatch
TEST_CATEGORY=simple_python sbatch jobs/run_backbone_eval.sbatch
```

현재 서버에서 실제로 사용한 job은 repo 밖 `/data/home/martellato41/research/run_bfcl_*.job`입니다. 다른 서버로 옮길 때는 submodule 안의 `jobs/*.sbatch`를 기준으로 경로와 conda env 이름만 맞추면 됩니다.

## 결과물 관리

BFCL 실행 산출물은 git에 넣지 않습니다.

```text
logs/
logger/
result/
score/
result_runs/
subset/
subset_runs/
experiments/**/outputs/
```

재현에 필요한 코드는 submodule에 포함하고, 모델 weight와 실행 결과는 서버 로컬에 둡니다.

## 원격 저장소 확인

top-level DiffuAgent:

```bash
git remote -v
# origin git@github.com:martellato51/DiffuAgent.git
```

Gorilla submodule:

```bash
git -C unified_envs/gorilla remote -v
# origin   git@github.com:martellato51/gorilla.git
# upstream https://github.com/ShishirPatil/gorilla
```

`ShishirPatil/gorilla`는 upstream 원본입니다. push 대상은 `origin`, 즉 `martellato51/gorilla`입니다.
