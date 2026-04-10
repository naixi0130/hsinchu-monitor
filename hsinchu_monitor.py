import streamlit as st
import feedparser
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from apify_client import ApifyClient

st.set_page_config(page_title="新竹縣社群監測器", page_icon="🏠", layout="wide")
st.title("🏠 新竹縣社群監測器")
st.caption("Google News + PTT + Dcard + Facebook Posts + Instagram Hashtag（已優化）")

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

# ==================== 基本平台 ====================
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
                "summary": getattr(entry, 'summary', '')[:250],
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
        for div in soup.find_all("div", class_="r-ent")[:10]:
            title_a = div.find("a")
            if title_a:
                posts.append({
                    "title": title_a.text.strip(),
                    "summary": "PTT 熱門討論 - 新竹縣相關",
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
            if any(x in (title + excerpt) for x in ["新竹縣", "新竹"]):
                created_time = datetime.fromtimestamp(post.get("createdAt", 0) / 1000)
                if created_time > datetime.now() - timedelta(hours=48):
                    posts.append({
                        "title": title,
                        "summary": excerpt[:250],
                        "time": created_time.strftime("%Y-%m-%d %H:%M"),
                        "platform": "Dcard",
                        "url": f"https://www.dcard.tw/f/post/{post.get('id')}"
                    })
        return posts
    except:
        return []

# ==================== Facebook Posts (改用較好的 Actor) ====================
def fetch_fb_posts():
    if "APIFY_API_TOKEN" not in st.secrets:
        return []
    try:
        client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
        run_input = {
            "query": "新竹縣",
            "maxResults": 15,
            "recentPosts": True   # 盡量抓較新的貼文
        }
        # 使用專門抓 Posts 的 Actor（較穩定）
        run = client.actor("scrapeforge/facebook-search-posts").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"]).iterate_items()
        posts = []
        now = datetime.now()
        for item in list(dataset)[:12]:
            title = item.get("text", "")[:80] or item.get("message", "")[:80] or "Facebook 貼文"
            summary = item.get("text", "") or item.get("message", "") or item.get("description", "")[:300]
            posts.append({
                "title": title,
                "summary": summary,
                "time": now.strftime("%Y-%m-%d %H:%M"),
                "platform": "Facebook",
                "url": item.get("url") or item.get("postUrl") or "#"
            })
        return posts
    except Exception as e:
        st.warning(f"Facebook 抓取失敗: {str(e)[:120]}")
        return []

# ==================== Instagram Hashtag ====================
def fetch_ig_hashtag():
    if "APIFY_API_TOKEN" not in st.secrets:
        return []
    try:
        client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
        run_input = {
            "hashtags": ["新竹縣", "竹北", "新竹"],
            "resultsLimit": 15,
            "searchLimit": 10
        }
        run = client.actor("apify/instagram-hashtag-scraper").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"]).iterate_items()
        posts = []
        for item in list(dataset)[:10]:
            caption = item.get("caption", "") or "Instagram 貼文"
            posts.append({
                "title": caption[:80],
                "summary": caption[:280],
                "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "platform": "Instagram",
                "url": item.get("url") or "#"
            })
        return posts
    except Exception as e:
        st.warning(f"Instagram 抓取失敗: {str(e)[:100]}")
        return []

# ==================== 主畫面 ====================
if st.button("🔥 一鍵抓取過去24小時（已優化 FB + IG）", type="primary", use_container_width=True):
    with st.spinner("抓取中... 這次會花較多時間（FB/IG 約 20-50 秒）"):
        news = fetch_google_news()
        ptt = fetch_ptt()
        dcard = fetch_dcard()
        fb = fetch_fb_posts()
        ig = fetch_ig_hashtag()
        
        all_posts = news + ptt + dcard + fb + ig
        
        categories = defaultdict(list)
        for post in all_posts:
            cat_key, _ = classify_post(post["title"], post.get("summary", ""))
            categories[cat_key].append(post)
        
        st.success(f"✅ 抓取完成！共 {len(all_posts)} 則討論")
        
        col1, col2, col3 = st.columns(3)
        for col, cat_name, key in zip([col1, col2, col3], 
                                      ["🔵 新竹縣政治", "🟠 新竹縣重大議題", "🟥 新竹縣天災人禍"], 
                                      ["politics", "issues", "disasters"]):
            with col:
                st.subheader(cat_name)
                st.caption(f"{len(categories[key])} 則")
                for p in categories[key]:
                    with st.expander(f"**{p['title'][:70]}...**", expanded=False):
                        st.caption(f"{p['platform']} • {p['time']}")
                        st.write(p.get('summary', '無內容摘要'))
                        if p.get('url') and p['url'] != "#":
                            st.link_button("🔗 查看原文", p['url'])

else:
    st.info("👆 點擊按鈕開始抓取\n\n※ FB/IG 這次已改用專門抓貼文的設定，內容應該會豐富許多")

st.markdown("---")
st.caption("已優化 Facebook Posts + Instagram Hashtag • 若 FB 還是只有少量內容，可改用特定社團名稱抓取")
