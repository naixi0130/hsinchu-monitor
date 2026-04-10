import streamlit as st
import feedparser
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from apify_client import ApifyClient

st.set_page_config(page_title="新竹縣社群監測器", page_icon="🏠", layout="wide")
st.title("🏠 新竹縣社群監測器")
st.caption("Google News + PTT + Dcard + Facebook + Instagram（Apify）")

st.markdown("---")

# 分類關鍵字
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

# ==================== 基本抓取 ====================
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
    url = "https://www.dcard.tw/service/api/v2/posts?limit=30"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        posts = []
        for post in data:
            title = post.get("title", "")
            excerpt = post.get("excerpt", "")
            if "新竹縣" in title or "新竹縣" in excerpt or "新竹" in title:
                created_time = datetime.fromtimestamp(post.get("createdAt", 0) / 1000)
                if created_time > datetime.now() - timedelta(hours=48):  # 放寬一點
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

# ==================== Apify FB + IG ====================
def fetch_fb_apify():
    if "APIFY_API_TOKEN" not in st.secrets:
        st.warning("未設定 APIFY_API_TOKEN，跳過 Facebook 抓取")
        return []
    try:
        client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
        run_input = {
            "searchQueries": ["新竹縣"],
            "maxResults": 20,
            "includePosts": True
        }
        # 使用較穩定的 Facebook Search Scraper
        run = client.actor("apify/facebook-search-scraper").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"]).iterate_items()
        posts = []
        now = datetime.now()
        cutoff = now - timedelta(hours=24)
        for item in list(dataset)[:15]:
            title = item.get("title") or item.get("name") or "Facebook 討論"
            summary = item.get("text") or item.get("description") or item.get("about", "")[:200]
            posts.append({
                "title": title,
                "summary": summary,
                "time": now.strftime("%Y-%m-%d %H:%M"),  # Apify 時間較複雜，先用現在時間
                "platform": "Facebook",
                "url": item.get("url") or item.get("facebookUrl") or "#"
            })
        return posts
    except Exception as e:
        st.error(f"Facebook 抓取錯誤: {str(e)[:100]}")
        return []

def fetch_ig_apify():
    if "APIFY_API_TOKEN" not in st.secrets:
        return []
    try:
        client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
        run_input = {
            "search": "新竹縣",
            "searchType": "hashtag",
            "resultsLimit": 20
        }
        run = client.actor("apify/instagram-scraper").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"]).iterate_items()
        posts = []
        for item in list(dataset)[:10]:
            caption = item.get("caption", "") or "Instagram 貼文"
            posts.append({
                "title": caption[:80],
                "summary": caption[:200],
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "platform": "Instagram",
                "url": item.get("url") or "#"
            })
        return posts
    except Exception as e:
        st.warning(f"Instagram 抓取錯誤: {str(e)[:80]}")
        return []

# ==================== 主畫面 ====================
if st.button("🔥 一鍵抓取過去24小時（含 FB + IG）", type="primary", use_container_width=True):
    with st.spinner("抓取中... Google News + PTT + Dcard + Facebook + Instagram（可能需 15-40 秒）"):
        news = fetch_google_news()
        ptt = fetch_ptt()
        dcard = fetch_dcard()
        fb = fetch_fb_apify()
        ig = fetch_ig_apify()
        
        all_posts = news + ptt + dcard + fb + ig
        
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
                with st.expander(f"**{p['title'][:60]}...**", expanded=False):
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'])
                    if p['url'] != "#":
                        st.link_button("🔗 查看原文", p['url'])
        
        with col2:
            st.subheader("🟠 新竹縣重大議題")
            st.caption(f"{len(categories['issues'])} 則")
            for p in categories['issues']:
                with st.expander(f"**{p['title'][:60]}...**", expanded=False):
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'])
                    if p['url'] != "#":
                        st.link_button("🔗 查看原文", p['url'])
        
        with col3:
            st.subheader("🟥 新竹縣天災人禍")
            st.caption(f"{len(categories['disasters'])} 則")
            for p in categories['disasters']:
                with st.expander(f"**{p['title'][:60]}...**", expanded=False):
                    st.caption(f"{p['platform']} • {p['time']}")
                    st.write(p['summary'])
                    if p['url'] != "#":
                        st.link_button("🔗 查看原文", p['url'])

else:
    st.info("👆 點擊按鈕開始抓取\n\n※ 第一次抓取 FB/IG 可能較慢，請耐心等待")

st.markdown("---")
st.caption("已整合 Apify • FB/IG 抓取使用免費額度，建議每天不要超過 3-5 次抓取")
