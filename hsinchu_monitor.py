import streamlit as st
import feedparser
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd

st.set_page_config(page_title="新竹縣社群監測器", page_icon="🏠", layout="wide")
st.title("🏠 新竹縣社群監測器")
st.caption("一鍵抓取過去24小時討論 • Google News + PTT + Dcard")

st.markdown("---")

# 關鍵字分類（更精準）
politics_keywords = ["選舉", "議員", "縣長", "立委", "政黨", "藍營", "綠營", "民進黨", "國民黨", "民眾黨", "柯文哲", "侯友宜", "鄭朝方", "林智堅"]
issues_keywords = ["竹北", "科學園區", "交通", "捷運", "高鐵", "房價", "開發", "環境", "空汙", "醫療", "教育"]
disaster_keywords = ["地震", "颱風", "淹水", "豪雨", "火災", "爆炸", "車禍", "意外", "天災", "災情", "傷亡"]

def classify_post(title, summary):
    text = (title + " " + summary).lower()
    if any(kw in text for kw in disaster_keywords):
        return "disasters", "🟥 新竹縣天災人禍"
    elif any(kw in text for kw in politics_keywords):
        return "politics", "🔵 新竹縣政治"
    else:
        return "issues", "🟠 新竹縣重大議題"

# ==================== 抓取函式 ====================
def fetch_google_news():
    url = "https://news.google.com/rss/search?q=%E6%96%B0%E7%AB%B9%E7%B8%A3&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    feed = feedparser.parse(url)
    posts = []
    now = datetime.now()
    cutoff = now - timedelta(hours=24)
    for entry in feed.entries:
        pub_date = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') else now
        if pub_date > cutoff:
            posts.append({
                "title": entry.title,
                "summary": getattr(entry, 'summary', '')[:200],
                "time": pub_date.strftime("%Y-%m-%d %H:%M"),
                "platform": "Google News",
                "url": entry.link
            })
    return posts

def fetch_ptt():
    # （保持原本 PTT 抓取）
    headers = {"User-Agent": "Mozilla/5.0"}
    session = requests.Session()
    session.cookies.set("over18", "1")
    url = "https://www.ptt.cc/bbs/Gossiping/search?q=%E6%96%B0%E7%AB%B9%E7%B8%A3"
    try:
        r = session.get(url, headers=headers, timeout=10)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        posts = []
        for div in soup.find_all("div", class_="r-ent")[:8]:
            title_a = div.find("a")
            if title_a:
                posts.append({
                    "title": title_a.text.strip(),
                    "summary": "PTT 熱門討論",
                    "time": "PTT 最近",
                    "platform": "PTT",
                    "url": "https://www.ptt.cc" + title_a["href"]
                })
        return posts
    except:
        return []

def fetch_dcard():
    """抓取 Dcard 最新貼文並篩選新竹縣相關"""
    url = "https://www.dcard.tw/service/api/v2/posts?limit=30"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        posts = []
        for post in data:
            title = post.get("title", "")
            excerpt = post.get("excerpt", "")
            if "新竹縣" in title or "新竹縣" in excerpt or "新竹" in title:
                created_time = datetime.fromtimestamp(post.get("createdAt", 0) / 1000)
                posts.append({
                    "title": title,
                    "summary": excerpt[:200],
                    "time": created_time.strftime("%Y-%m-%d %H:%M"),
                    "platform": "Dcard",
                    "url": f"https://www.dcard.tw/f/post/{post.get('id')}"
                })
        return posts
    except:
        return []

# ==================== 主程式 ====================
if st.button("🔥 一鍵抓取過去24小時最新討論（含 Dcard）", type="primary", use_container_width=True):
    with st.spinner("正在抓取 Google News + PTT + Dcard..."):
        news = fetch_google_news()
        ptt = fetch_ptt()
        dcard = fetch_dcard()
        all_posts = news + ptt + dcard
        
        categories = defaultdict(list)
        for post in all_posts:
            cat_key, _ = classify_post(post["title"], post.get("summary", ""))
            categories[cat_key].append(post)
        
        st.success(f"✅ 抓取完成！共 {len(all_posts)} 則討論（Google News + PTT + Dcard）")
        
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
    st.info("👆 點擊上方按鈕開始抓取（已包含 Dcard）")

st.markdown("---")
st.caption("✅ 已加入 Dcard • FB/IG 需要付費工具才能穩定抓取，需再告訴我")
