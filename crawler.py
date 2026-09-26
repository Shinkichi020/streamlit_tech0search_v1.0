import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional

############################################################
# crawl_url()
############################################################

def crawl_url(url: str) -> dict:
    """
    URLをクロールして情報を返す（fetch → parse のワンストップ）

    Args:
        url: クロール対象URL
    
    Return:
        ページ情報の辞書（失敗時も crawl_status で判断可能
    """
    # HTML取得
    html = fetch_page(url)

    # 取得失敗時
    if not html:
        return {
            "url": url,
            "crawl_status": "failed",
            "crawled_at": datetime.now().isoformat(),
            "error": "Failed to fetch page",
        }

    try:
        # 取得成功時は解析して返す
        return parse_html(html, url)

    except Exception as e:
        # 解析失敗時
        return {
            "url": url,
            "crawl_status": "error",
            "crawled_at": datetime.now().isoformat(),
            "error": str(e)
        }

############################################################
# fetch_page()
############################################################

def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """
    指定URLのHTMLを取得する。

    Args:
        url: 取得対象URL
        timeout: タイムアウト秒数
    
    Returns:
        HTML文字列。失敗時は None
    """
    try:
        # User-Agentを指定してアクセスする
        headers = {"User-Agent": "Tech0SearchBot/1.0 (Educational Purpose)"}

        # Webページにアクセス
        resp = requests.get(url, headers=headers, timeout=timeout)

        # エラーコードなら例外を発生させる
        resp.raise_for_status()

        # 文字コードを推定して設定
        resp.encoding = resp.apparent_encoding

        # HTML全文を返す
        return resp.text

    except requests.RequestException as e:
        # 取得失敗時は None を返す
        return None

############################################################
# parse_html()
############################################################

def parse_html(html: str, url: str) -> dict:
    """
    HTMLを解析してページ情報を抽出する。

    Args:
        html: HTML文字列
        url: 元URL
    
    Returns:
        抽出した情報の辞書
    """
    # HTMLをBeatifulSoupで解析
    soup = BeautifulSoup(html, "html.parser")

    # 不要タグを除去
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose

    # タイトル取得
    title = "No Title"
    if soup.find("title"):
        title = soup.title.text
    elif soup.find("h1"):
        title = soup.h1.text

    # meta description
    description = "No Description"
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = meta["content"][:200]

    # meta keywords
    keywords = []
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    if meta_kw and meta_kw.get("content"):
        for kw in meta_kw["content"].split(","):
            keywords.append(kw.strip())
        keywords = keywords[:10]

    # 本文テキスト
    paragraphs = soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "td"])
    full_text = ""
    for p in paragraphs:
        full_text = " ".join([full_text, p.get_text().strip()])
    full_text = re.sub(r"\s+", " ", full_text).strip()

    # リンク
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http"):
            links.append(href)
    links = links[:20]

    # 辞書にまとめる
    return {
        "url": url,
        "title": title,
        "description": description,
        "keywords": keywords,
        "full_text": full_text,
        "links": links,
        "word_count": len(full_text.split()),
        "crawled_at": datetime.now().isoformat(),
        "crawl_status": "success",
    }
