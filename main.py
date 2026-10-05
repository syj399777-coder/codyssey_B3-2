import os
import sys
import re
import argparse
import subprocess
import requests
from typing import Tuple, Optional

# ==========================================
# 1. Git 정보 수집 모듈
# ==========================================

def run_git_command(command: list[str]) -> Tuple[bool, str]:
    """Git 명령어를 실행하고 결과를 반환합니다."""
    try:
        result = subprocess.run(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
    check=True
)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()
    except FileNotFoundError:
        return False, "Git이 설치되어 있지 않거나 PATH에 등록되지 않았습니다."

def get_git_changes(safe_mode: bool = False) -> Tuple[str, str]:
    """Git status 및 diff 결과를 수집합니다."""
    # Git 루트 디렉토리 확인
    is_git, _ = run_git_command(["git", "rev-parse", "--is-inside-work-tree"])
    if not is_git:
        print("[ERROR] 현재 디렉토리가 Git 저장소가 아닙니다.")
        sys.exit(1)

    # status 수집
    _, status_output = run_git_command(["git", "status", "--porcelain"])
    if not status_output:
        print("[INFO] 변경 사항이 없습니다. 커밋/PR 메시지를 생성하지 않고 종료합니다.")
        sys.exit(0)

    # diff 수집 (Staged + Unstaged 변경사항 모두 포함)
    _, diff_output = run_git_command(["git", "diff", "HEAD"])
    if not diff_output:
        # unstaged diff가 없다면 staged diff만 시도
        _, diff_output = run_git_command(["git", "diff", "--cached"])

    if safe_mode and diff_output:
        diff_output = apply_safe_mode(diff_output)

    return status_output, diff_output

def apply_safe_mode(diff_text: str) -> str:
    """안전 모드: 민감정보 마스킹 및 최대 줄 수(200줄) 제한"""
    print("[INFO] Safe Mode 적용 중: 민감정보 마스킹 및 diff 길이 제한")
    
    # 1. 민감 정보 정규식 마스킹 (API Key, Email 등)
    # API 키 / Token 패턴
    diff_text = re.sub(r'(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*["\']?([^"\'\s]+)["\']?', r'\1: [MASKED]', diff_text)
    # 이메일 주소 패턴
    diff_text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL_MASKED]', diff_text)

    # 2. Diff 줄 수 제한 (최대 200줄)
    lines = diff_text.splitlines()
    if len(lines) > 200:
        diff_text = "\n".join(lines[:200]) + f"\n\n... [Safe Mode: 나머지 {len(lines) - 200}줄 생략됨] ..."

    return diff_text

# ==========================================
# 2. AI API 연동 모듈
# ==========================================

def call_ai_api(prompt: str, system_message: str, model: str, temperature: float, max_tokens: int) -> str:
    """AI REST API를 호출하여 응답을 받습니다."""
    api_key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] AI_API_KEY (또는 OPENAI_API_KEY) 환경변수가 설정되지 않았습니다.")
        print("설정 예시: export AI_API_KEY=\"your_api_key_here\"")
        sys.exit(1)

    api_url = os.getenv("AI_API_URL", "https://api.openai.com/v1/chat/completions")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    print(f"[INFO] AI API 요청 중... (Model: {model}, Temp: {temperature}, MaxTokens: {max_tokens})")
    print("[INFO] API 호출 횟수: 1회")

    try:
        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] AI API 호출 실패: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR] 상세 응답 내용: {e.response.text}")
        sys.exit(1)

# ==========================================
# 3. 프롬프트 및 후처리 검증 모듈
# ==========================================

def generate_commit_message(status: str, diff: str, args) -> str:
    """커밋 메시지 생성 프롬프트 구하기 및 호출"""
    system_msg = (
        "당신은 엄격한 Git 커밋 메시지 작성 도무미입니다. 아래 규칙을 정확히 따르세요.\n"
        "1. 커밋 제목은 1줄로 50자 이내(최대 72자)로 요약 작성하세요.\n"
        "2. 접두사(feat, fix, refactor, docs, chore 등)를 반드시 사용하세요.\n"
        "3. 본문에는 변경된 핵심 파일 1~3개 언급 및 핵심 변경사항 1~2개를 불릿(-)으로 작성하세요."
    )
    prompt = f"### Git Status:\n{status}\n\n### Git Diff:\n{diff}"

    content = call_ai_api(prompt, system_msg, args.model, args.temperature, args.max_tokens)
    return validate_and_clean_commit(content)

def generate_pr_description(status: str, diff: str, args) -> str:
    """PR 제목 및 본문 생성 프롬프트 구하기 및 호출"""
    system_msg = (
        "당신은 Pull Request 작성을 돕는 AI 개발 보조도구입니다.\n"
        "반드시 다음 템플릿 형식을 준수하여 작성하세요.\n\n"
        "PR Title: <80자 이내의 PR 제목>\n\n"
        "## Why\n"
        "- <변경 배경 1개 이상>\n\n"
        "## What\n"
        "- <핵심 변경 사항 1개 이상>\n\n"
        "## How to Test\n"
        "- <테스트 방법 1개 이상>"
    )
    prompt = f"### Git Status:\n{status}\n\n### Git Diff:\n{diff}"

    content = call_ai_api(prompt, system_msg, args.model, args.temperature, args.max_tokens)
    return validate_and_clean_pr(content)

def validate_and_clean_commit(text: str) -> str:
    """커밋 메시지 형식 검증 및 다듬기"""
    lines = [line for line in text.splitlines() if line.strip()]
    if lines:
        # 제목 길이가 72자를 초과하면 자름
        if len(lines[0]) > 72:
            lines[0] = lines[0][:69] + "..."
    return "\n".join(lines)

def validate_and_clean_pr(text: str) -> str:
    """PR 설명 템플릿 검증 후 구획 출력 보장"""
    # 필수 헤더 검증
    required_headers = ["## Why", "## What", "## How to Test"]
    for header in required_headers:
        if header not in text:
            # 헤더가 없으면 강제로 보완 형태 제공
            text += f"\n\n{header}\n- [작성 필요] 요약 내용을 확인하세요."
    return text

# ==========================================
# 4. CLI 메인 핸들러
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="Git 변경 사항 기반 커밋/PR 자동 생성 도구")
    subparsers = parser.add_subparsers(dest="command", required=True, help="수행할 작업 선택 (commit 또는 pr)")

    # 공통 인수 설정 함수
    def add_common_args(p):
        p.add_argument("--model", type=str, default="gemini-3.8-flash", help="사용할 AI 모델 (기본값: gemini-2.5-flash)")
        p.add_argument("--temperature", type=float, default=0.2, help="생성 다양성 조절 (기본값: 0.2)")
        p.add_argument("--max-tokens", type=int, default=500, help="최대 토큰 수 (기본값: 500)")
        p.add_argument("--safe-mode", action="store_true", help="안전 모드 활성화 (민감정보 마스킹 및 diff 제한)")

    # commit 명령어
    commit_parser = subparsers.add_parser("commit", help="커밋 메시지 생성")
    add_common_args(commit_parser)

    # pr 명령어
    pr_parser = subparsers.add_parser("pr", help="PR 제목/본문 생성")
    add_common_args(pr_parser)

    args = parser.parse_args()

    # Git status 및 diff 수집
    status_output, diff_output = get_git_changes(safe_mode=args.safe_mode)

    print(f"[INFO] Git status 수집 완료")
    print(f"[INFO] Git diff 수집 완료 ({len(diff_output.splitlines())}줄)")

    print("=" * 60)
    if args.command == "commit":
        result = generate_commit_message(status_output, diff_output, args)
        print("[DONE] 커밋 메시지 생성 완료\n")
        print("------------------- Commit Message -------------------")
        print(result)
        print("------------------------------------------------------")
    elif args.command == "pr":
        # 현재 브랜치 정보 수집
        _, branch_name = run_git_command(["git", "branch", "--show-current"])
        print(f"[INFO] 현재 브랜치: {branch_name}")
        result = generate_pr_description(status_output, diff_output, args)
        print("[DONE] PR 초안 생성 완료\n")
        print("---------------------- PR Draft ----------------------")
        print(result)
        print("------------------------------------------------------")
    print("=" * 60)

if __name__ == "__main__":
    main()