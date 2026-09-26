-- schema.sql
-- Tech0 Search データベース設計（W3：データ基盤の最小構成）

-- pagesテーブル（メイン）
-- UNIQUE 制約：同じ URL は重複して登録できない
CREATE TABLE IF NOT EXISTS pages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL UNIQUE,
    title       TEXT NOT NULL,
    description TEXT,
    full_text   TEXT,
    author      TEXT,
    category    TEXT,
    keywords    TEXT,                    -- カンマ区切りで保存（例: "DX,営業店,業務効率"）
    word_count  INTEGER DEFAULT 0,
    crawled_at  DATETIME,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- keywordsテーブル（TF-IDFスコア保存用。実際に使うのは W4）
CREATE TABLE IF NOT EXISTS keywords (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page_id     INTEGER NOT NULL,
    keyword     TEXT NOT NULL,
    tf_score    REAL DEFAULT 0.0,
    tfidf_score REAL DEFAULT 0.0,
    FOREIGN KEY (page_id) REFERENCES pages(id) ON DELETE CASCADE
);

-- インデックス作成（検索を高速化する）
CREATE INDEX IF NOT EXISTS idx_keyword ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_page_id ON keywords(page_id);

-- ※ search_logs / click_logs テーブルは W6（発展課題）で追加します。
