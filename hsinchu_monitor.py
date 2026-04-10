import streamlit as st
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="新竹縣社群監測器", page_icon="🏠", layout="wide")
st.title("🏠 新竹縣社群監測器")
st.caption("一鍵抓取過去24小時討論 • 自動分類 • Google News + PTT")

st.markdown("---")

# 關鍵字分類
politics_keywords = ["選舉", "議員", "縣長", "立委", "政黨", "藍營", "綠營", "民進黨", "國民黨", "民眾黨", "柯文哲", "侯友宜", "鄭朝方", "林智堅", "竹北市", "頭前溪"]
issues_keywords = ["竹北", "科學園區", "交通", "捷運", "高鐵", "房價", "開發", "環境", "空汙", "醫療", "教育", "建設"]
disaster_keywords = ["地震", "颱風", "淹水", "豪雨", "火災", "爆炸", "車禍", "意外", "天災", "災情", "傷亡"]

def classify_post(title, summary):
    text = (title + " " + summary).lower()
    if any(kw in text for kw in disaster_keywords):
        return "disasters", "🟥 新竹縣天災人禍"
    elif any(kw in text for kw in politics_keywords):
        return "politics", "🔵 新竹縣政治"
    else:
        return "issues", "🟠 新竹縣重大議題"

# 抓取 Google News（24小時）
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
                "summary": entry.summary[:200] + "..." if hasattr(entry, 'summary') and len(entry.summary) > 200 else (getattr(entry, 'summary', '')),
                "time": pub_date.strftime("%Y-%m-%d %H:%M"),
                "platform": "Google News",
                "url": entry.link
            })
    return posts

# 抓取 PTT
def fetch_ptt():
    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    session.cookies.set("over18", "1")
    url = "https://www.ptt.cc/bbs/Gossiping/search?q=%E6%96%B0%E7%AB%B9%E7%B8%A3"
    try:
        r = session.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        posts = []
        for div in soup.find_all("div", class_="r-ent")[:10]:
            title_a = div.find("a")
            if title_a:
                title = title_a.text.strip()
                link = "https://www.ptt.cc" + title_a["href"]
                posts.append({
                    "title": title,
                    "summary": "PTT 熱門討論",
                    "time": "PTT 最近",
                    "platform": "PTT",
                    "url": link
                })
        return posts
    except:
        return []

# 主畫面
if st.button("🔥 一鍵抓取過去24小時最新討論", type="primary", use_container_width=True):
    with st.spinner("正在抓取 Google News + PTT 並自動分類..."):
        news_posts = fetch_google_news()
        ptt_posts = fetch_ptt()
        all_posts = news_posts + ptt_posts
        
        categories = defaultdict(list)
        for post in all_posts:
            cat_key, _ = classify_post(post["title"], post.get("summary", ""))
            categories[cat_key].append(post)
        
        st.success(f"✅ 抓取完成！共 {len(all_posts)} 則討論")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🔵 新竹縣政治")
            st.caption(f"{len(categories['politics'])} 則")
            for p in categories['politics']:
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'][:180] + "..." if len(p['summary']) > 180 else p['summary'])
                    st.link_button("🔗 查看原文", p['url'])
        
        with col2:
            st.subheader("🟠 新竹縣重大議題")
            st.caption(f"{len(categories['issues'])} 則")
            for p in categories['issues']:
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'][:180] + "..." if len(p['summary']) > 180 else p['summary'])
                    st.link_button("🔗 查看原文", p['url'])
        
        with col3:
            st.subheader("🟥 新竹縣天災人禍")
            st.caption(f"{len(categories['disasters'])} 則")
            for p in categories['disasters']:
                with st.container(border=True):
                    st.markdown(f"**{p['title']}**")
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'][:180] + "..." if len(p['summary']) > 180 else p['summary'])
                    st.link_button("🔗 查看原文", p['url'])

else:
    st.info("👆 點擊上方按鈕開始抓取最新討論")

st.markdown("---")
st.caption("目前支援 Google News + PTT • 想加 X（Twitter）即時抓取請告訴我")
