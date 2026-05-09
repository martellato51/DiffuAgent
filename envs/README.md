# Reproducible Conda Environments

이 폴더는 DiffuAgent/BFCL 재현에 필요한 conda environment 예시입니다.

## BFCL에서 직접 쓰는 환경

- `qwen3.yml`
  - Qwen3-8B를 vLLM OpenAI-compatible server로 띄우는 환경입니다.
  - `backbone/qwen3-8b` BFCL 평가에 사용합니다.
- `llada8b.yml`
  - LLaDA-8B-Instruct를 Fast-dLLM v1 코드로 local inference하는 환경입니다.
  - `backbone/llada` BFCL 평가와 think-parallel diagnostic에 사용합니다.

## 함께 보관하는 환경

- `llada2.1.yml`
  - LLaDA2.1-mini legacy smoke/eval 환경입니다.
  - 현재 BFCL backbone 재현의 기본 경로에는 쓰지 않지만, 같은 연구 세팅을 보존하기 위해 함께 둡니다.

## 생성 예시

```bash
conda env create -f envs/qwen3.yml
conda env create -f envs/llada8b.yml
```

`llada8b.yml`의 torch CUDA wheel은 서버 CUDA/driver 조합에 따라 추가 설치가 필요할 수 있습니다. BFCL setup job은 BFCL editable install, Fast-dLLM v1 requirements, model registration을 별도로 수행합니다.
