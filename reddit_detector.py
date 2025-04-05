import praw
import os
import json
import gspread
import time
import nltk
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone
from pytz import timezone as pytz_timezone

# === Step 1: Reddit API Setup ===
reddit = praw.Reddit(
    client_id=os.environ["REDDIT_CLIENT_ID"],
    client_secret=os.environ["REDDIT_CLIENT_SECRET"],
    username=os.environ["REDDIT_USERNAME"],
    password=os.environ["REDDIT_PASSWORD"],
    user_agent="script:reddit.outage.tracker:v1.0 (by u/Moneybeast_blog)"
)

# === Step 2: Subreddits & Keywords Setup ===
subreddits_to_check = [
    "Helldivers", "Palworld", "ApexLegends", "CSGO", "CounterStrike", "Valorant",
    "Fortnite", "Roblox", "Minecraft", "PUBG", "Battlefield", "CallOfDuty", "Warzone",
    "RustConsole", "Rust", "EscapeFromTarkov", "DayZ", "DeadbyDaylight", "Phasmophobia",
    "Eldenring", "DarkSouls2", "DarkSouls3", "Sekiro", "LethalCompany", "HuntShowdown",
    "GTA", "GTAV", "RDR2", "Cyberpunkgame", "Starfield", "TheCycleGame", "TheForest",
    "SonsOfTheForest", "ProjectZomboid", "Arma", "Arma3", "Squad", "Insurgency", "ReadyOrNotGame",
    "DestinyTheGame", "Overwatch", "Overwatch2", "TeamFortress2", "Dota2", "LeagueOfLegends",
    "Genshin_Impact", "Warframe", "Farlight84", "AmongUs", "Rainbow6", "Smite", "Tarkov",
    "BaldursGate3", "PathOfExile", "Diablo", "MonsterHunterWorld", "Terraria",
    "StardewValley", "HadesTheGame", "NoMansSky", "Seaofthieves", "FallGuysGame",
    "Instagram", "Snapchat", "WhatsApp", "YouTube", "Facebook", "Twitter", "Reddit",
    "Spotify", "DiscordApp", "Telegram", "Zoom", "Google", "Gmail", "Twitch", "Netflix",
    "Hulu", "PrimeVideo", "Uber", "DoorDash", "CashApp", "Venmo", "PayPal", "ChatGPT",
    "MidJourney", "CharacterAI", "Notion", "Canva", "Drive", "Outlook", "LinkedIn", "Teams",
    "CapCut", "Adobe", "Dropbox", "Steam", "EpicGamesPC", "PlayStation", "Xbox", "XboxSupport"
]

keywords = [
    "server down", "outage", "not working", "connection error", "matchmaking issue",
    "login failed", "can't connect", "connection lost", "disconnected", "server issue",
    "crashing", "black screen", "freeze", "lagging", "maintenance", "api error",
    "servers offline", "service unavailable", "kick", "timeout", "failed to load"
]

# === Step 3: Search Reddit Posts ===
results = []
for subreddit in subreddits_to_check:
    try:
        for post in reddit.subreddit(subreddit).new(limit=100):
            post_title = post.title.lower()
            if any(keyword in post_title for keyword in keywords) and post.score >= 7:
                title_sentiment_score = analyzer.polarity_scores(post.title)['compound']
                title_sentiment_label = (
                    "Positive" if title_sentiment_score > 0.2 else
                    "Negative" if title_sentiment_score < -0.2 else
                    "Neutral"
                )

                post.comments.replace_more(limit=0)
                top_comments = post.comments[:10]
                comment_sentiments = [
                    analyzer.polarity_scores(comment.body)['compound'] for comment in top_comments
                ]

                if comment_sentiments:
                    avg_comment_sentiment = sum(comment_sentiments) / len(comment_sentiments)
                    comment_sentiment_label = (
                        "Positive" if avg_comment_sentiment > 0.2 else
                        "Negative" if avg_comment_sentiment < -0.2 else
                        "Neutral"
                    )
                else:
                    comment_sentiment_label = "No Comments"

                results.append({
                    "post": post,
                    "title_sentiment": title_sentiment_label,
                    "comment_sentiment": comment_sentiment_label
                })
    except Exception as e:
        print(f"⚠️ Failed to fetch from r/{subreddit}: {e}")

print(f"✅ Fetched {len(results)} matching outage posts.")

# === Step 4: Google Sheets Auth ===
google_creds = json.loads(os.environ["GOOGLE_SHEETS_JSON"])
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(google_creds, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open("Reddit Outages").sheet1

# === Step 5: Define Game Subreddits ===
game_subs = [
    "Helldivers", "Palworld", "ApexLegends", "CSGO", "CounterStrike", "Valorant", "Fortnite",
    "Roblox", "Minecraft", "PUBG", "Battlefield", "CallOfDuty", "Warzone", "RustConsole",
    "Rust", "EscapeFromTarkov", "DayZ", "DeadbyDaylight", "Phasmophobia", "Eldenring",
    "DarkSouls2", "DarkSouls3", "Sekiro", "LethalCompany", "HuntShowdown", "GTA", "GTAV",
    "RDR2", "Cyberpunkgame", "Starfield", "TheCycleGame", "TheForest", "SonsOfTheForest",
    "ProjectZomboid", "Arma", "Arma3", "Squad", "Insurgency", "ReadyOrNotGame",
    "DestinyTheGame", "Overwatch", "Overwatch2", "TeamFortress2", "Dota2", "LeagueOfLegends",
    "Genshin_Impact", "Warframe", "Farlight84", "AmongUs", "Rainbow6", "Smite", "Tarkov",
    "BaldursGate3", "PathOfExile", "Diablo", "LostArk", "MonsterHunterWorld", "Payday2",
    "Payday3", "Terraria", "StardewValley", "HadesTheGame", "NoMansSky", "Seaofthieves",
    "FallGuysGame"
]

# === Step 6: Upload to Sheet ===
rows_to_add = []
for result in results:
    post = result["post"]
    row = [
        "Game" if post.subreddit.display_name in game_subs else "App",
        post.subreddit.display_name,
        post.title,
        post.url,
        datetime.fromtimestamp(post.created_utc, timezone.utc).strftime('%Y-%m-%d %H:%M'),
        result["title_sentiment"],
        result["comment_sentiment"]
    ]
    rows_to_add.append(row)

try:
    if rows_to_add:
        sheet.append_rows(rows_to_add, value_input_option="USER_ENTERED")
        print(f"📊 ✅ Uploaded {len(rows_to_add)} rows to Google Sheets!")
    else:
        print("⚠️ No matching posts to upload.")

    all_data = sheet.get_all_values()
    headers = all_data[0]
    data_rows = all_data[1:]

    seen_urls = set()
    fresh_rows = []
    cutoff_time = datetime.now(timezone.utc).timestamp() - 86400

    for row in data_rows:
        try:
            date_str = row[4]
            row_timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp()
            if row[3] not in seen_urls and row_timestamp >= cutoff_time:
                seen_urls.add(row[3])
                fresh_rows.append(row)
        except Exception as e:
            print(f"⚠️ Skipped row due to date parsing issue: {row} — {e}")

    sheet.clear()
    sheet.append_row(headers)
    sheet.append_rows(fresh_rows, value_input_option="USER_ENTERED")
    print(f"♻️ Cleaned {len(data_rows) - len(fresh_rows)} old or duplicate rows.")

except Exception as e:
    print(f"🚫 Error during upload or deduplication: {e}")

# === Step 8: Add Last Updated Timestamp ===

# === Step 8: Add Last Updated Timestamp ===

# === Step 8: Add Last Updated Timestamp (IST only) ===
try:
    now_ist = datetime.now(pytz_timezone("Asia/Kolkata"))
    timestamp = now_ist.strftime("Last Updated: %Y-%m-%d %H:%M IST")

    sheet.update('A1', timestamp)
    print("🕒 Added last updated timestamp (IST).")
except Exception as e:
    print(f"⚠️ Failed to update timestamp: {e}")


    sheet.update('A1', timestamp)
    print("🕒 Added last updated timestamp (IST).")
except Exception as e:
    print(f"⚠️ Failed to update timestamp: {e}")
