#!/usr/bin/env python3
"""
Apple整備済製品ページを監視し、iPhone 16シリーズが入荷したらメール通知するスクリプト。

環境変数（GitHub Actions の Secrets 経由で渡す想定）:
  GMAIL_ADDRESS      : 送信元Gmailアドレス（例: yourname@gmail.com）
  GMAIL_APP_PASSWORD : Gmailの「アプリパスワード」（通常のログインパスワードではない）
  NOTIFY_TO          : 通知を受け取るメールアドレス（送信元と同じでも可）

チェック対象: https://www.apple.com/jp/shop/refurbished/iphone
検知キーワード: "iPhone 16"（このページの商品タイトルに "iPhone 16" という文字列が
含まれるかどうかで判定します）
"""

import os
import re
import sys
import smtplib
import urllib.request
from email.mime.text import MIMEText

URL = "https://www.apple.com/jp/shop/refurbished/iphone"
KEYWORD = "iPhone 16"
STATE_FILE = "last_state.txt"  # 前回の検知結果を保存（GitHub Actions ではキャッシュ/コミットで永続化）


def fetch_page(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="ignore")


def extract_matches(html: str, keyword: str) -> list[str]:
    """商品名っぽい見出し(<h3>や<a>内)からキーワードを含む行を抽出する簡易版"""
    # ページ内テキストからキーワードを含む商品名候補を抜き出す
    # (Apple側のマークアップ変更に強くするため、正規表現は緩めに)
    pattern = re.compile(r"[^<>\n]{0,40}" + re.escape(keyword) + r"[^<>\n]{0,60}")
    matches = pattern.findall(html)
    # 重複除去
    seen = set()
    result = []
    for m in matches:
        m = m.strip()
        if m and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def send_email(subject: str, body: str) -> None:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_password = os.environ["GMAIL_APP_PASSWORD"]
    notify_to = os.environ.get("NOTIFY_TO", gmail_address)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = notify_to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [notify_to], msg.as_string())


def load_last_state() -> str:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_last_state(state: str) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(state)


def main() -> None:
    try:
        html = fetch_page(URL)
    except Exception as e:
        print(f"[ERROR] ページ取得に失敗しました: {e}", file=sys.stderr)
        sys.exit(1)

    matches = extract_matches(html, KEYWORD)
    found = len(matches) > 0
    current_state = "FOUND" if found else "NOT_FOUND"
    last_state = load_last_state()

    print(f"現在の状態: {current_state} / 前回の状態: {last_state or '(なし)'}")
    if found:
        print("検出内容:")
        for m in matches:
            print(f"  - {m}")

    # 「前回は在庫なし」→「今回は在庫あり」に変わった時だけ通知する
    if current_state == "FOUND" and last_state != "FOUND":
        body_lines = [
            "Appleの整備済製品ページでiPhone 16シリーズの在庫を検知しました。",
            "",
            f"URL: {URL}",
            "",
            "検出された商品:",
        ] + [f"- {m}" for m in matches]
        send_email(
            subject="【在庫復活】整備済iPhone 16 の在庫を検知しました",
            body="\n".join(body_lines),
        )
        print("通知メールを送信しました。")

    save_last_state(current_state)


if __name__ == "__main__":
    main()
