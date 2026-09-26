import sqlite3
import json
from pathlib import Path
from datetime import datetime

# DB ファイルのパス（data/ サブフォルダに保存する）
DB_PATH = Path("data/tech0_search.db")

def get_connection():
    """
    DB への接続を取得する。

    raw_factory を設定することで、行データを辞書のように扱える。
    data/ フォルダが存在しない場合は自動で作成する。
    """
    DB_PATH.parent.mkdir(exist_ok=True)  # data/ フォルダがなければ作る
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row       # 行データを辞書のように扱う
    return conn


def init_db():
    """
    schema.sql を読み込んで DB を初期化する。

    CREATE TABLE IF NOT EXISTS を使っているので、
    すでにテーブルが存在する場合は何もしない。
    """
    conn = get_connection()
    with open("schema.sql", "r", encoding="utf-8") as f:
        conn.executescript(f.read())    # SQL ファイルをまとめて実行する
    conn.commit()
    conn.close()


def _keywords_to_text(keywords) -> str:
    """keywords（リスト or 文字列）を DB 保存用のカンマ区切り文字列にする"""
    if not keywords:
        return ""
    if isinstance(keywords, str):
        return keywords
    return ",".join(keywords)


def insert_page(page: dict) -> int:
    """
    ページ情報を DB に登録する。

    INSERT OR REPLACE：同じ URL のデータがあれば上書き、なければ新規追加する。
    これにより「同じページを再クロールしたときに最新データに更新できる」。

    Args:
        page: ページ情報の辞書（crawl_url() の返り値と同形式）

    Returns:
        登録された行の id
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO pages
            (url, title, description, full_text, author, category, keywords, word_count, crawled_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        page["url"],
        page["title"],
        page.get("description", ""),
        page.get("full_text", ""),
        page.get("author", ""),
        page.get("category", ""),
        _keywords_to_text(page.get("keywords")),   # リスト → "DX,営業店" にして保存
        page.get("word_count", 0),
        page.get("crawled_at", datetime.now().isoformat()),
    ))

    page_id = cursor.lastrowid    # 登録された行の id を取得する
    conn.commit()
    conn.close()
    return page_id


def get_all_pages() -> list:
    """全ページを登録日時の新しい順で取得する。"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pages ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    pages = []
    for row in rows:
        pg = dict(row)
        # 保存時にカンマ区切りにした keywords をリストに戻す
        pg["keywords"] = [k.strip() for k in (pg.get("keywords") or "").split(",") if k.strip()]
        pages.append(pg)
    return pages    # sqlite3.Row を辞書に変換して返す


def log_search(query: str, results_count: int, user_id: str = None) -> int:
    """
    検索ログを記録する（W6 の発展課題で実装予定）
    現在はスタブ（空の関数）として定義しています。
    W6 の発展課題で実際の記録処理を実装します。
    """
    pass  # W6 の発展課題で実装します


def migrate_from_json(json_path: str = "pages_w2.json") -> int:
    """
    W2 で使っていた JSON のデータを、まるごと DB に移す。

    Args:
        json_path: 移行元のJSONファイル

    Returns:
        移行した件数
    """
    # ① JSONファイルを読む（W2 でやったのと同じ）
    with open(json_path, "r", encoding="utf-8") as f:
        pages = json.load(f)

    # ② 1件ずつ DB に入れる（Step 2-2 で作った insert_page を使うだけ）
    for p in pages:
        insert_page(p)

    return len(pages)