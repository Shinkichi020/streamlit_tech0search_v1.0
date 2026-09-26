import streamlit as st
import time
from database import init_db, get_all_pages, insert_page, log_search
from ranking  import get_engine, rebuild_index
from crawler import crawl_url

# アプリ起動時に DB を初期化する（テーブルが未作成なら作る）
init_db()

# ページ設定・タイトルエリア
st.set_page_config(page_title="Tech0 Search v1.0", page_icon="🔍", layout="wide")
st.title("🔍 Tech0 Search v1.0")
st.caption("PROJECT ZERO ― 社内ナレッジ検索エンジン")

# キャッシュ付きインデックス構築
@st.cache_resource
def load_and_index():
    pages = get_all_pages()     # DB から全ページを取得
    if pages:
        rebuild_index(pages)    # TF-IDF インデックスを構築する
    return pages

pages = load_and_index()
engine = get_engine()

# タブエリア
tab1, tab2, tab3 = st.tabs(["検索","クロール","一覧"])

# コンテンツエリア ― タブ1 ― 検索
with tab1:
    st.subheader("🔍 キーワード検索")

    col_search, col_options = st.columns([3, 1])
    with col_search:
        query = st.text_input(
            "キーワードを入力", 
            placeholder= "例: DX, AI, 融資"
        ) 
    with col_options:
        top_n = st.selectbox("表示件数", [10, 20, 50], index=0)

    if query:
        results = engine.search(query, top_n=top_n) 
        log_search(query, len(results))     # 検索するたびに自動記録
        st.markdown(f"**{query}の検索結果： {len(results)} 件**（TF-IDFスコア順）")
        st.divider()

        if results:
            for i, page in enumerate(results, 1):
                with st.container():
                    col_rank, col_title, col_score = st.columns([0.5, 4, 1])
                    with col_rank:
                        # 上位3件にはメダルを表示
                        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else str(i)
                        st.markdown(f"### {medal}")
                    with col_title:
                        st.markdown(f"### {page['title']}")
                    with col_score:
                        st.metric("スコア", f"{page['relevance_score']}", delta=f"基準： {page['base_score']}")

                    desc = page.get("description", "")
                    if desc:
                        st.markdown(f"*{desc[:200]}{'...' if len(desc) > 200 else ''}*")

                    kw = page.get("keywords", "") or ""
                    if kw:
                        kw_list = [k.strip() for k in kw.split(",")] if isinstance(kw, str) else list(kw)
                        tags = " ".join([f"`{k}`" for k in kw_list[:5] if k])
                        st.markdown(f"🏷️ {tags}")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.caption(f"👤 {page.get('author', '不明') or '不明'}")
                    with col2:
                        st.caption(f"📊 {page.get('word_count', 0)} 語")
                    with col3:
                        st.caption(f"📁 {page.get('category', '未分類') or '未分類'}")
                    with col4:
                        st.caption(f"📅 {(page.get('crawled_at', '') or '')[:10]}")

                    st.markdown(f"🔗 [{page['url']}]({page['url']})")
                st.divider()

        else:
            st.info("該当するページが見つかりませんでした")

# コンテンツエリア ― タブ2 ― クロール（一括。登録先がDBに変更）
import re

if "crawl_results" not in st.session_state:
    st.session_state.crawl_results = []

with tab2:
    st.subheader("🤖 自動クローラー")

    if st.session_state.get("registered_count"):
        st.success(f"{st.session_state['registered_count']} 件 登録完了！")
        st.session_state["registered_count"] = 0
    st.caption("URLを入力してクロールし、インデックスに登録する")

    crawl_url_input = st.text_area(
        "クロール対象URL",
        placeholder= "URLを改行またはスペース区切りで入力してください",
        height=150
    )

    if st.button("🤖 クロール実行", type="primary"):
        if crawl_url_input:
            raw_parts = re.split(r'[\s]+', crawl_url_input.strip())
            urls = [p for p in raw_parts if p.startswith(("http://", "https://"))]

            if not urls:
                st.error("有効なURLが見つかりませんでした")
            else:
                st.write(f"🔗 {len(urls)}件のURLを処理します")

                st.session_state.crawl_results = []

                for url in urls:
                    with st.spinner(f"クロール中： {url}"):
                        result = crawl_url(url)

                    if result and result.get('crawl_status') == 'success':
                        st.success(f"✅ 成功： {url}")

                        col1, col2 = st.columns(2)
                        with col1:
                            title = result.get('title', '')
                            st.metric("📄 タイトル", (title[:30] + "...") if len(title) > 30 else title)
                        with col2:
                            st.metric("📊 文字数", f"{result.get('word_count', 0)} 語")

                        st.session_state.crawl_results.append(result)

                    else:
                        st.error(f"❌ 失敗： {url}")

    if st.session_state.crawl_results:
        st.info(f"{len(st.session_state.crawl_results)}件のクロール結果を登録できます。")

        if st.button("💾 全てインデックスに登録"):
            total = len(st.session_state.crawl_results)

            progress_text = st.empty()
            progress_bar = st.progress(0)

            for i, r in enumerate(st.session_state.crawl_results, start=1):
                progress_text.write(f"✒️ {i} / {total} 件登録中...")
                insert_page(r)
                progress_bar.progress(i / total)

            st.session_state["registered_count"] = total
            st.session_state.crawl_results = []
            st.cache_resource.clear()
            st.rerun()


# コンテンツエリア ― タブ3 ― 一覧
with tab3:
    st.subheader(f"📚 登録済みページ一覧 {len(pages)}件")
    if not pages:
        st.info("登録されているページがありません。クロールタブからページを追加してください。")
    else:
        for page in pages:
            with st.expander(f"📄 {page['title']}"):
                st.markdown(f"**URL：** {page['url']}")
                st.markdown(f"**説明：** {page.get('description', '（なし）') or '（なし）'}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"語数： {page.get('word_count', 0)}")
                with col2:
                    st.caption(f"作成者： {page.get('author', '不明') or '不明'}")
                with col3:
                    st.caption(f"カテゴリ： {page.get('category', '未分類') or '未分類'}")

st.divider()
st.caption("@ 2026 PROJECT ZERO ― Tech0 Search v1.0 | Powered by TF-IDF") 
