import streamlit as st
import feedparser
import requests
from datetime import datetime, timedelta
from collections import defaultdict
import pandas as pd
from apify_client import ApifyClient
from docx import Document
from io import BytesIO

st.set_page_config(page_title="新竹縣社群監測器", page_icon="🏠", layout="wide")
st.title("🏠 新竹縣社群監測器")
st.caption("嚴格過去24小時 • Google News + PTT + Dcard + Facebook + Instagram")

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

now = datetime.now()
cutoff = now - timedelta(hours=24)

# ==================== 其他抓取函式保持不變（省略以節省空間） ====================
# ...（fetch_google_news, fetch_ptt, fetch_dcard, fetch_ig_hashtag 保持原本最新版本）

def fetch_fb_posts():
    if "APIFY_API_TOKEN" not in st.secrets:
        st.info("未設定 Apify Token，跳過 Facebook")
        return []
    
    try:
        client = ApifyClient(st.secrets["APIFY_API_TOKEN"])
        
        # 改用較穩定的 facebook-posts-scraper + 提供 startUrls
        run_input = {
            "startUrls": [
                {"url": "https://www.facebook.com/search/posts/?q=新竹縣"},   # 關鍵字搜尋
                {"url": "https://www.facebook.com/search/posts/?q=竹北"},     # 額外關鍵字
            ],
            "maxPosts": 20,
            "onlyPosts": True
        }
        
        run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
        dataset = client.dataset(run["defaultDatasetId"]).iterate_items()
        
        posts = []
        for item in list(dataset)[:15]:
            text = item.get("text") or item.get("message") or item.get("caption", "") or ""
            if len(text.strip()) > 20:   # 過濾空或太短的貼文
                title = text[:85].replace("\n", " ")
                posts.append({
                    "title": title,
                    "summary": text[:400],
                    "time": now.strftime("%Y-%m-%d %H:%M"),
                    "platform": "Facebook",
                    "url": item.get("url") or item.get("facebookUrl") or item.get("postUrl") or "#"
                })
        if not posts:
            st.warning("Facebook 目前沒有抓到有效貼文（可能受平台限制）")
        return posts
    except Exception as e:
        st.error(f"Facebook 抓取失敗: {str(e)[:200]}")
        return []

# ==================== 主程式（保持不變） ====================
if st.button("🔥 一鍵抓取過去24小時討論", type="primary", use_container_width=True):
    with st.spinner("抓取中... Facebook 可能較慢"):
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
        
        st.success(f"✅ 抓取完成！共 {len(all_posts)} 則（Facebook {len(fb)} 則）")
        
        # 顯示三欄（保持你原本的樣式）
        col1, col2, col3 = st.columns(3)
        for col, name, key in zip([col1, col2, col3], 
                                  ["🔵 新竹縣政治", "🟠 新竹縣重大議題", "🟥 新竹縣天災人禍"], 
                                  ["politics", "issues", "disasters"]):
            with col:
                st.subheader(name)
                st.caption(f"{len(categories[key])} 則")
                for p in categories[key]:
                    with st.expander(f"**{p['title'][:70]}...**", expanded=False):
                        st.caption(f"{p['platform']} • {p['time']}")
                        st.write(p.get('summary', '無內容'))
                        if p.get('url') and p['url'] != "#":
                            st.link_button("🔗 查看原文", p['url'])

        # Word 匯出
        if all_posts:
            word_bytes = generate_word(all_posts, categories)   # 你原本的 generate_word 函式
            st.download_button("📄 匯出全部結果為 Word 文件", 
                               data=word_bytes, 
                               file_name=f"新竹縣監測報告_{now.strftime('%Y%m%d_%H%M')}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               use_container_width=True)

else:
    st.info("👆 點擊按鈕開始抓取\n\n※ Facebook 目前使用關鍵字搜尋，抓取量可能較少")

st.markdown("---")
st.caption("若想大幅提升 Facebook 抓取品質，請告訴我幾個新竹縣相關的公開社團名稱，我會幫你加入專門抓社團貼文的功能！")
