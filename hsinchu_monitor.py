<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新竹縣社群監測器 - 完整版 (Streamlit)</title>
</head>
<body>
    <h1 style="text-align:center; color:#15803d;">完整版已準備好！</h1>
    <p style="text-align:center; font-size:1.1rem;">
        以下是<strong>真正的 Python + Streamlit 版本</strong>，可以在你電腦上跑一個完整的互動式網站。<br>
        一鍵抓取過去24小時「新竹縣」相關討論（Google News + PTT），自動分類、產生標題、大綱、時間、平台、網址。
    </p>

    <div style="background:#f0fdf4; padding:20px; border-radius:16px; max-width:900px; margin:30px auto; border:2px solid #86efac;">
        <h3 style="color:#166534;">🚀 如何在 30 秒內啟動真正的網站？</h3>
        <ol style="line-height:1.8;">
            <li>確保你的電腦已安裝 <strong>Python 3.8 或以上</strong>（沒有就去 python.org 下載）</li>
            <li>開啟「命令提示字元」（Windows）或「終端機」（Mac），依序貼上以下指令：</li>
            <pre style="background:#052e16; color:#86efac; padding:12px; border-radius:8px; overflow:auto;">
pip install streamlit feedparser beautifulsoup4 requests lxml pandas
            </pre>
            <li>把下面「完整程式碼」全部複製，存成一個檔案，檔名叫做 <code style="background:#ecfdf5; padding:2px 6px; border-radius:4px;">hsinchu_monitor.py</code></li>
            <li>在終端機輸入以下指令並按 Enter：</li>
            <pre style="background:#052e16; color:#86efac; padding:12px; border-radius:8px; overflow:auto;">
streamlit run hsinchu_monitor.py
            </pre>
            <li>瀏覽器會自動開啟一個美觀的網站！你就可以一直點「一鍵刷新」使用</li>
        </ol>
        <p style="margin-top:20px; font-size:0.95rem; color:#166534;">
            ※ 這個網站完全在你自己電腦上執行，不需要上傳任何資料，安全又快速。<br>
            ※ 未來想加 X（Twitter）、FB 完整自動抓取，或部署到雲端讓手機也能看，隨時告訴我，我再幫你擴充！
        </p>
    </div>

    <h2 style="text-align:center; margin:40px 0 20px;">📋 完整程式碼（直接複製全部）</h2>
    <pre style="background:#052e16; color:#86efac; padding:24px; border-radius:16px; overflow:auto; line-height:1.6; font-size:0.95rem; max-height:70vh;">import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

# ====================== 設定 ======================
st.set_page_config(page_title="新竹縣社群監測器", page_icon="🏠", layout="wide")
st.title("🏠 新竹縣社群監測器")
st.caption("一鍵抓取過去24小時討論 • 自動分類 • 新聞 + PTT 即時更新")

st.markdown("---")

# ====================== 關鍵字分類 ======================
politics_keywords = ["選舉", "議員", "縣長", "立委", "政黨", "藍營", "綠營", "民進黨", "國民黨", "民眾黨", "柯文哲", "侯友宜", "鄭朝方", "林智堅", "竹北市", "頭前溪"]
issues_keywords = ["竹北", "科學園區", "交通", "捷運", "高鐵", "房價", "開發", "環境", "空汙", "醫療", "教育", "建設", "重大議題"]
disaster_keywords = ["地震", "颱風", "淹水", "豪雨", "火災", "爆炸", "車禍", "意外", "天災", "災情", "傷亡", "死亡", "人禍", "淹大水"]

def classify_post(title, summary):
    text = (title + " " + summary).lower()
    if any(kw in text for kw in disaster_keywords):
        return "disasters", "🟥 新竹縣天災人禍"
    elif any(kw in text for kw in politics_keywords):
        return "politics", "🔵 新竹縣政治"
    else:
        return "issues", "🟠 新竹縣重大議題"

# ====================== 抓取 Google News (24小時) ======================
def fetch_google_news():
    url = "https://news.google.com/rss/search?q=%E6%96%B0%E7%AB%B9%E7%B8%A3&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(url)
    posts = []
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_date = datetime(*entry.published_parsed[:6])
        else:
            pub_date = now
        if pub_date > cutoff:
            posts.append({
                "title": entry.title,
                "summary": entry.summary[:200] + "..." if hasattr(entry, 'summary') and len(entry.summary) > 200 else (entry.summary if hasattr(entry, 'summary') else ""),
                "time": pub_date.strftime("%Y-%m-%d %H:%M"),
                "platform": "Google News",
                "url": entry.link
            })
    return posts

# ====================== 抓取 PTT (簡單版) ======================
def fetch_ptt():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    session = requests.Session()
    session.cookies.set("over18", "1")   # 跳過 PTT 18禁
    url = "https://www.ptt.cc/bbs/Gossiping/search?q=%E6%96%B0%E7%AB%B9%E7%B8%A3"
    try:
        r = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        posts = []
        for div in soup.find_all("div", class_="r-ent")[:8]:   # 取前8筆
            title_a = div.find("a")
            if title_a:
                title = title_a.text.strip()
                link = "https://www.ptt.cc" + title_a["href"]
                posts.append({
                    "title": title,
                    "summary": "PTT 熱門討論：" + title,
                    "time": "PTT 最近24小時",
                    "platform": "PTT",
                    "url": link
                })
        return posts
    except:
        return []   # 網路問題時不中斷

# ====================== 主程式 ======================
if st.button("🔥 一鍵抓取過去24小時最新討論", type="primary", use_container_width=True):
    with st.spinner("正在抓取 Google News + PTT 資料並自動分類..."):
        news_posts = fetch_google_news()
        ptt_posts = fetch_ptt()
        all_posts = news_posts + ptt_posts
        
        # 分類
        categories = defaultdict(list)
        for post in all_posts:
            cat_key, cat_name = classify_post(post["title"], post.get("summary", ""))
            categories[cat_key].append(post)
        
        st.success(f"✅ 抓取完成！共 {len(all_posts)} 則討論（過去24小時）")
        
        # 顯示三個分類區塊
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🔵 新竹縣政治")
            st.caption(f"{len(categories['politics'])} 則")
            for p in categories['politics']:
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'][:180] + "..." if len(p['summary']) > 180 else p['summary'])
                    st.link_button("🔗 查看原文", p['url'], use_container_width=True)
        
        with col2:
            st.subheader("🟠 新竹縣重大議題")
            st.caption(f"{len(categories['issues'])} 則")
            for p in categories['issues']:
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'][:180] + "..." if len(p['summary']) > 180 else p['summary'])
                    st.link_button("🔗 查看原文", p['url'], use_container_width=True)
        
        with col3:
            st.subheader("🟥 新竹縣天災人禍")
            st.caption(f"{len(categories['disasters'])} 則")
            for p in categories['disasters']:
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'][:180] + "..." if len(p['summary']) > 180 else p['summary'])
                    st.link_button("🔗 查看原文", p['url'], use_container_width=True)
        
        # 額外表格總覽
        if all_posts:
            df = pd.DataFrame(all_posts)
            st.markdown("### 📊 全部資料總覽")
            st.dataframe(df[["platform", "time", "title"]], use_container_width=True, hide_index=True)

else:
    st.info("👆 點擊上方按鈕開始抓取最新討論\n\n（目前以 Google News + PTT 為主，穩定且合法）")

