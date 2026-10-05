[초기설정]

# 1. 제미나이 API 키 설정
export AI_API_KEY="AIzaSy로_시작하는_실제_Gemini_키_입력"

제미나이(Gemini) 무료 API Key 발급받기
Google AI Studio Get API key 웹사이트에 접속하여 구글 계정으로 로그인합니다.

[Create API key] 버튼을 누른 후 새 프로젝트를 선택하여 API 키를 생성합니다.

화면에 생성된 AIzaSy...로 시작하는 긴 문자열(API Key)을 복사해 둡니다.

# 2. 제미나이 OpenAI 호환 주소 설정
export AI_API_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

# 3. 키가 정상 적용되었는지 확인 (설정한 키가 출력되면 성공)
echo $AI_API_KEY


---

[테스트 시]

# 1. VS Code에서 README.md (또는 test.txt) 파일 열기

# 2. 파일 아무 곳에나 아무 내용 추가 후 저장 (Ctrl + S / Cmd + S)

# 3. 저장 후 아래 명령어 실행 (커밋 메시지 생성 테스트)
python main.py commit

# 4. PR 초안 생성 테스트
python main.py pr

---


# AI Git Commit & PR Assistant 🤖

Git 변경 사항(`git status`, `git diff`)을 분석하여 컨벤션에 맞는 **커밋 메시지**와 **Pull Request(PR) 초안**을 자동으로 생성해주는 CLI 도구입니다.

---

## 💡 주요 기능
- **Git 변경 사항 자동 분석**: `git status` 및 `git diff` 수집
- **AI 기반 커밋 메시지 생성**: 50자 이내의 제목 + 핵심 요약 불릿
- **템플릿 준수 PR 작성**: `Why`, `What`, `How to Test` 구획 자동 구성
- **안전 모드 (`--safe-mode`)**: API Key, 비밀번호, 이메일 마스킹 및 전송 diff 길이 제한(200줄)
- **파라미터 커스텀**: 모델, temperature, max-tokens 조정 가능

---


## 📋 프로젝트 평가 및 설계 검증 (Self-Assessment)

### [항목 1] 동작 검증 및 기능 테스트 결과

1. **커밋 메시지 및 PR 제목/본문 터미널 출력**
   - `ppython main.py commit` 실행, 변경 사항 요약 기반의 커밋 메시지(제목 1줄 + 불릿 본문)가 터미널에 명확한 구획선과 함께 출력됩니다.
   - `python main.py pr` 실행 시, PR 제목 1줄과 `Why/What/How to Test` 템플릿이 적용된 PR 초안이 터미널에 출력됩니다.
   - [python main.py commit 실행]
   - <img width="595" height="225" alt="Image" src="https://github.com/user-attachments/assets/d09d2bc7-7370-4f3c-a820-dbd151e2564c" />

   -[python main.py pr 실행] 
   - <img width="774" height="377" alt="Image" src="https://github.com/user-attachments/assets/5a335cf7-3da5-4336-b4a1-99f92cb20d76" />

3. **API Key 미설정 상황 예외 처리**
   - `AI_API_KEY` 환경변수가 설정되지 않은 상태에서 실행할 경우, `[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.`라는 명확한 에러 메시지와 설정 가이드를 출력한 후 안전하게 프로그램을 종료(`sys.exit(1)`)합니다.
   - 
<img width="466" height="122" alt="Image" src="https://github.com/user-attachments/assets/795c9c2a-cd60-4330-bd69-e00ee236a21a" />

4. **Git 변경 사항이 없는 경우 처리**
   - `git status` 및 `git diff` 결과가 비어있는 경우 `[INFO] 변경 사항이 없습니다. 커밋/PR 메시지를 생성하지 않고 종료합니다.` 메시지를 출력하고 API 호출 없이 즉시 종료됩니다.
   - 
<img width="509" height="74" alt="Image" src="https://github.com/user-attachments/assets/a18dee7f-24c4-4f57-be87-d4e8c9fd1bae" />


5. **PR 본문 필수 구조 및 불릿 준수**
   - 생성된 PR 본문에는 `## Why`, `## What`, `## How to Test` 3개 섹션 헤더가 반드시 포함되며, 각 섹션 아래에는 최소 1개 이상의 불릿(`-`) 형태 설명이 생성됩니다.

6. **`--temperature` 및 `--max-tokens` 옵션 변경 실험 결과**
   - `--temperature 0.1`: 매우 단정적이고 일관된 어조로 핵심만 요약함.
   - `--temperature 0.8`: 표현이 다채로워지지만 불필요한 수식어가 늘어남.
   - `--max-tokens 100`: 길어진 diff 요약 도중 문장이 중간에 잘리는 현상이 발생함. (기본값 500 토큰 추천)

7. **길이 및 형식 규칙 만족**
   - 커밋 제목은 최대 72자(50자 권장)로 자동 잘림/제한 처리됩니다.
   - PR 제목은 80자 이내로 제한되며, 구획선(`---`)을 통해 결과물을 한눈에 알아볼 수 있도록 시각적으로 구분했습니다.

---

### [항목 2] 코드 구조 설계 및 구현 원리

1. **Git 수집 로직과 AI API 호출 로직을 분리한 이유**
   - **단일 책임 원칙(SRP)**과 **모듈 재사용성**을 위해 분리했습니다.
   - Git 수집 로직(`get_git_changes`)은 로컬 시스템 명령을 다루고, API 호출 로직(`call_ai_api`)은 외부 네트워크 통신을 다룹니다.
   - 두 로직을 분리해 두면 향후 AI API 제공업체를 교체(예: OpenAI → Anthropic)하더라도 Git 수집 코드는 전혀 수정할 필요가 없습니다.

2. **프롬프트 구성과 출력 포맷팅(후처리) 로직의 분리 이유**
   - **프롬프트 구성**: AI에게 원하는 형태를 요청하는 역할 (소프트한 제어)
   - **출력 포맷팅**: AI의 응답 결과가 규칙을 벗어났는지 검증하고 정제하는 역할 (하드한 제어)
   - LLM(대형 언어 모델)은 비결정론적이어서 프롬프트 지시를 100% 완벽히 따르지 않을 가능성이 존재합니다. 따라서 2단계로 분리하여 후처리 코드(`validate_and_clean_*`)에서 글자 수 자르기, 필수 헤더 강제 포함 등을 검증함으로써 검증된 결과물만 출력되도록 보장했습니다.

3. **API 파라미터를 CLI 옵션으로 설계한 이유 (재현성 및 실험 용이성)**
   - 소스 코드를 직접 수정하지 않고도 터미널 명령어 인자(`--model`, `--temperature`, `--max-tokens`)만으로 생성 파라미터를 유연하게 조절할 수 있습니다.
   - 개발자가 다양한 프로젝트 환경과 diff 크기에 맞춰 최적의 옵션을 신속하게 실험하고 재현할 수 있습니다.

4. **오류 처리 구현 방식 및 이유**
   - API Key 누락 체크, `requests.exceptions.RequestException` 예외 처리, Git 저장소 여부 검사 등을 사전에 배치했습니다.
   - 파이썬 복잡한 추적 오류(Traceback)가 사용자에게 노출되는 대신, `[ERROR]` 지표와 함께 원인 해결 방법을 직관적인 메시지로 알려주어 사용자 경험(UX)을 향상시켰습니다.

---

### [항목 3] AI API 파라미터 및 프롬프트 엔지니어링

1. **`temperature` 값의 영향**
   - **높은 값 (예: 0.8)**: 응답의 무작위성과 창의성이 증가하지만, 코드 변경 내역과 상관없는 가짜 사실(환각 현상)을 지어낼 위험이 커집니다.
   - **낮은 값 (예: 0.1 ~ 0.2)**: 결정론적이고 일관된 응답을 보장합니다. 정확성과 정형화된 요약이 생명인 Git 커밋/PR 생성에는 낮게 설정하는 것이 유리합니다.

2. **`max_tokens` 값의 영향 및 설정 기준**
   - API가 생성할 수 있는 최대 텍스트 길이를 제한합니다.
   - 불필요하게 무한정 길어지는 답변을 막아 **API 비용 폭증을 방지**합니다.
   - 커밋 메시지와 PR 설명 초안 작성에 충분한 정보량인 **500 토큰**을 기본값으로 설정했습니다.

3. **프롬프트 구성 정보 및 설계 이유**
   - **System Message**: AI의 역할(Git 커밋 작성 보조자), 필수 헤더 규칙(`Why/What/How to Test`), 글자 수 제한 규칙을 명확한 규칙문 형태로 지정했습니다.
   - **User Prompt**: `git status`로 변경된 파일 목록 맥락을 제공하고, `git diff`로 실제 수정 내용을 전달했습니다.
   - 단순 변경 파일 이름뿐만 아니라 차이점(diff)을 함께 주어야 코드 작성자의 의도와 배경을 AI가 정확히 추론할 수 있기 때문입니다.

4. **"재생성" 대신 "후처리" 방식을 선택한 이유**
   - **비용과 속도(Latency) 최적화** 때문입니다.
   - 형식이 조금 어긋났다고 AI API를 다시 호출(재생성)하면 API 요금이 이중으로 발생하고 사용자 대기 시간이 늘어납니다.
   - 1회 호출로 받은 텍스트를 파이썬의 문자열 연산(자르기, 검사)으로 다듬는 **후처리(Post-processing)** 방식이 훨씬 경제적이고 빠른 응답을 제공합니다.

---

### [항목 4] 운영, 보안 및 개발 확장 관점

1. **AI 생성 텍스트를 바로 사용하지 않고 검토가 필요한 이유**
   - **도메인 맥락 결여**: AI는 diff 텍스트만 읽을 수 있을 뿐, 기획 배경이나 실제 비즈니스 요구사항의 깊은 의도까지 파악하지는 못합니다.
   - **환각(Hallucination) 방지**: AI가 변경되지 않은 기능에 대해 서술하거나 잘못된 테스트 방법을 제안할 수 있으므로, 최종 커밋/PR 전 사용자의 Human-in-the-loop 검토가 반드시 필요합니다.

2. **Git Diff 내 민감정보 유출 위험 및 방지 방안**
   - **위험 상황**: 실수로 소스 코드 내에 API Key, DB 접속 패스워드, 개인 이메일, 개인정보 등을 작성한 상태에서 `git diff`를 수집하면 민감정보가 외부 AI API 서버로 전송될 수 있습니다.
   - **방지 방안**:
     - `--safe-mode` 옵션을 구현하여 정규표현식(Regex) 기반으로 API Key, Token, Password, Email 패턴을 `[MASKED]` 문구로 자동 치환 후 전송합니다.
     - 전송되는 diff의 길이를 최대 200줄로 제한하여 과도한 정보 전송을 차단합니다.
     - `.gitignore` 설정을 통해 환경변수 파일(`.env`)이나 비밀 정보 파일이 Git 관리 대상에 들어가지 않도록 철저히 관리합니다.

3. **팀 프로젝트 적용 시 최우선 개선/추가 기능 (우선순위 근거)**
   - **1순위 기능**: **팀 커밋/PR 컨벤션 파일(`.ai-gitgen.yml`) 연동 기능**
   - **우선순위 근거**: 팀마다 사용하는 커밋 모듈 태그(예: `feat`, `fix`, `chore` 등)나 PR 템플릿 항목이 다릅니다. 각 팀의 저장소 루트에 컨벤션 파일을 두고 이를 읽어와 프롬프트에 자동 반영되도록 개선한다면, 팀 전원이 동일한 규칙의 커밋/PR 문서를 자동으로 유지할 수 있어 실제 팀 협업에 가장 파급력이 큽니다.


---
    [requests의 역할]
   requests가 없으면 파이썬 프로그램이 외부 인터넷(구글 API 서버)과 통신을 하지 못합니다.

---
[--temperature` 및 `--max-tokens` 옵션 변경]

1. --temperature (창의성 / 일관성) 실험

# 1) Temperature = 0.0 (최대한 단정하고 정형화된 표현)
python main.py commit --temperature 0.0

# 2) Temperature = 0.9 (다채롭고 자유로운 표현)
python main.py commit --temperature 0.9

2. --max-tokens (최대 답변 길이 제한) 실험

# 1) Max Tokens = 30 (극도로 짧게 제한)
python main.py commit --max-tokens 30

# 2) Max Tokens = 500 (기본값: 충분한 길이 제공)
python main.py commit --max-tokens 500

