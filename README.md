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

위 명령은 SSH key가 있는 서버 기준입니다. 새 서버에 GitHub SSH key가 없다면 먼저 key를 등록하거나, clone 후 submodule URL을 HTTPS/인증 가능한 URL로 바꿔야 합니다.

이미 clone한 뒤라면:

```bash
git submodule update --init --recursive
```

확인:

```bash
git status --branch --short
git -C unified_envs/gorilla status --branch --short
```

submodule은 기본적으로 특정 commit에 고정되므로 `HEAD (no branch)`로 보일 수 있습니다. submodule 안에서 코드를 수정할 때만 아래처럼 branch를 checkout합니다.

```bash
cd unified_envs/gorilla
git checkout diffuagent-bfcl
```

## 포함된 BFCL 내용

Gorilla submodule 안의 주요 파일:

```text
unified_envs/gorilla/berkeley-function-call-leaderboard/
├── README_BFCL_BACKBONE.md
├── register_backbone.py
├── jobs/
│   ├── setup_bfcl_env.sbatch       # 환경 설치 진입점
│   ├── run_bfcl_qwen3.job          # Qwen3-8B 평가
│   ├── run_bfcl_llada.job          # LLaDA-8B 평가
│   └── run_bfcl_singleturn_eval.job  # 평가만 (generate 없이)
├── bfcl_eval/
│   ├── build_handlers_backbone.py
│   └── model_handler/api_inference/diffuagent/
│       ├── handlers_backbone.py
│       └── ENV_CONFIG.md
└── bfcl_eval/scripts/
    └── make_bfcl_subsets_ids.py
```

등록되는 backbone 모델은 두 개입니다.

- `backbone/qwen3-8b`: Qwen3-8B를 vLLM OpenAI-compatible server로 띄워 BFCL 평가.
- `backbone/llada`: LLaDA-8B-Instruct를 Fast-dLLM v1 코드로 Python 프로세스 안에서 직접 로드해 BFCL 평가.

## 필요한 외부 폴더

repo에 포함되지 않는 모델 snapshot과 외부 checkout은 서버별로 준비해야 합니다.

```text
<research>/
├── DiffuAgent/
├── Fast-dLLM/
│   └── v1/llada/
<model_root>/
├── Qwen3-8B/
└── LLaDA-8B-Instruct/
```

## 새 서버 설정

**`jobs/env.sh` 파일 하나만 수정하면 됩니다.** 이 파일에 서버별 경로가 모두 모여 있고, 모든 job 파일이 이를 source합니다.

```bash
cd unified_envs/gorilla/berkeley-function-call-leaderboard
vi jobs/env.sh   # 아래 8개 항목을 본인 서버에 맞게 수정
```

수정할 항목:

```bash
BFCL_ROOT            # 이 repo의 berkeley-function-call-leaderboard 경로
CONDA_SH             # miniconda 또는 anaconda의 conda.sh 경로
QWEN_PYTHON          # qwen3 conda env의 python 바이너리 경로
LLADA_PYTHON         # llada8b conda env의 python 바이너리 경로
MAIN_AGENT_MODEL_PATH  # Qwen3-8B 모델 weight 디렉터리
LLADA_MODEL_PATH       # LLaDA-8B-Instruct 모델 weight 디렉터리
FAST_DLLM_LLADA_PATH   # Fast-dLLM v1/llada 코드 디렉터리
CUDA_VISIBLE_DEVICES   # 사용할 GPU 번호 (예: "0,1" 또는 "1,2,3")
```

수정 후 설치와 실행:

```bash
# 환경 설치 (qwen3, llada8b conda env 모두 세팅)
bash jobs/setup_bfcl_env.sbatch

# Qwen3-8B 싱글턴 평가
export TEST_CATEGORIES="simple_python,multiple,parallel,parallel_multiple,simple_java,simple_javascript,live_simple,live_multiple,live_parallel,live_parallel_multiple"
runlog bash jobs/run_bfcl_qwen3.job

# LLaDA-8B 멀티턴 평가
export TEST_CATEGORIES="multi_turn_base"
runlog bash jobs/run_bfcl_llada.job
```

자세한 내용은 `README_BFCL_BACKBONE.md`를 참고합니다.

## 결과물 관리

BFCL 실행 산출물은 git에 넣지 않습니다.

```text
logs/
logger/
result/
result_runs/
score/
subset/
subset_runs/
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
