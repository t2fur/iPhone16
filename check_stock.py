#!/usr/bin/env python3
"""
Apple整備済製品ページを監視し、iPhone 16シリーズが入荷したらメール通知するスクリプト。

環境変数（GitHub Actions の Secrets 経由で渡す想定）:
  GMAIL_ADDRESS      : 送信元Gmailアドレス（例: yourname@gmail.com）
  GMAIL_APP_PASSWORD : Gmailの「アプリパスワード」（通常のログインパスワードではない）
  NOTIFY_TO          : 通知を受け取るメールアドレス（送信元と同じでも可）

チェック対象: https://www.apple.com/jp/shop/refurbished/iphone
検知キーワード: "iPhone 16"（実際の商品ページへのリンクを持つ商品名にこの文字列が
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


def strip_non_content(html: str) -> str:
    """<script>や<style>タグの中身を除去する。
    Appleのページには商品フィルター用のJavaScript設定データ(JSON)が
    埋め込まれており、そこに "iPhone 16 Pro Max" 等の文字列が
    (実際の在庫の有無に関係なく)常に含まれているため、誤検知の原因になる。
    """
    html = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style\b[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    return html


def extract_matches(html: str, keyword: str) -> list[str]:
    """実際に購入可能な商品一覧だけからキーワードを含む商品名を抽出する。

    Appleのページには「モデルで絞り込む」フィルター欄があり、在庫の有無に
    関わらず全モデル名（グレーアウト状態のものも含む）が常にHTML上に
    表示されている。これをそのまま検索すると在庫がなくても誤検知してしまう。

    実際に購入可能な商品は必ず個別の商品ページへのリンク
    (例: /jp/shop/product/xxxxx/a/iphone-15-...) を持つため、
    そのリンクのテキスト部分だけを対象に検索することで、
    フィルター欄などの「表示だけ」の要素を除外する。
    """
    content_html = strip_non_content(html)

    # /shop/product/ へのリンクを持つ <a>...</a> のテキスト部分を抽出
    link_pattern = re.compile(
        r'<a\b[^>]*href="[^"]*/shop/product/[^"]*"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    seen = set()
    result = []
    for link_html in link_pattern.findall(content_html):
        # タグを除去してプレーンテキスト化
        text = re.sub(r"<[^>]+>", " ", link_html)
        text = re.sub(r"\s+", " ", text).strip()
        if keyword in text and text not in seen:
            seen.add(text)
            result.append(text)
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
