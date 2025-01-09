import feedparser

# feed_url = "https://www.brainyquote.com/link/quotebr.rss"
# feed = feedparser.parse(feed_url)
# for entry in feed.entries:
#     print(entry.title)
#     print(entry.link)
#     print(entry.description)
#

rss_url = "https://feeds.content.dowjones.io/public/rss/mw_topstories"
feed = feedparser.parse(rss_url)

for entry in feed.entries:
    print("Title:", entry.title)
    print("Link:", entry.link)
    print("Published:", entry.published)
    print(entry.description)

    print("-----")