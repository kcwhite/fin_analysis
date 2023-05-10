import json
import logging

import grequests
import requests
import yfinance as yf
from bs4 import BeautifulSoup
# noinspection PyPackageRequirements
from textblob import TextBlob

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_name_from_ticker(ticker_symbol):
    logging.info(f"Fetching company name for {ticker_symbol}")
    try:
        return yf.Ticker(ticker_symbol).info['shortName']
    except Exception as e:
        logging.error(f"Error while fetching ticker symbol for {ticker_symbol}: {e}")


def read_file(file_path):
    with open(file_path, 'r') as file:
        lines = [line.strip() for line in file]
    return lines


def scrape_content(url, hdrs):
    content = []
    try:
        response = requests.get(url, headers=hdrs)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for title in soup.find_all('h1'):
                content.append(title.text.strip())
            for paragraph in soup.find_all('p'):
                content.append(paragraph.text.strip())
        else:
            logging.warning(f"Non-200 response ({response.status_code}) for URL: {url}")
    except Exception as e:
        logging.error(f"Error while scraping content: {e}")
    return ' '.join(content)


def request_content(url, hdrs):
    return grequests.get(url, headers=hdrs)


def analyze_sentiment(text):
    analysis = TextBlob(text)
    sentiment_score = (analysis.sentiment.polarity + 1) * 5
    return sentiment_score


def predict_stock_trend(links, hdrs):
    rs = (request_content(url, hdrs) for url in links)
    responses = grequests.map(rs)

    content_list = [scrape_content(response.url, hdrs) for response in responses if response]
    sentiment_scores = [analyze_sentiment(content) for content in content_list]

    items = [
        {
            "website": response.url,
            "content": content,
            "score": score
        }
        for response, content, score in zip(responses, content_list, sentiment_scores) if response
    ]

    if sentiment_scores:
        return sum(sentiment_scores) / len(sentiment_scores), items
    else:
        return None, items


def save_results_to_json(res, file_name='results.json'):
    with open(file_name, 'w') as f:
        json.dump(res, f, indent=2)


def save_summary_to_txt(res, file_name='summary.txt'):
    with open(file_name, 'w') as f:
        for company, data in res.items():
            f.write(f"{company}: {data['avg_score']:.2f}\n")


def get_news_links(tkr):
    try:
        news = yf.Ticker(tkr).news
    except Exception as e:
        print(f"Error retrieving news for {tkr}: {e}")
        return []

    # Extract links
    links = []
    for item in news:
        try:
            links.append(item['link'])
        except KeyError:
            continue  # Skip if no 'link' key

    return links


if __name__ == "__main__":
    tickers = read_file('ticker-symbols.txt')

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) "
                      "Version/14.0.3 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    results = {}

    for ticker in tickers:
        company_name = get_name_from_ticker(ticker)
        company_key = f"{ticker}" + (f" ({company_name})" if company_name else "")
        news_links = get_news_links(ticker)

        logging.info(f"Analyzing sentiment for {company_key}")

        # Update predict_stock_trend function to return content_list and sentiment_scores as well
        average_sentiment, news_items = predict_stock_trend(news_links, headers)

        if average_sentiment is not None:
            logging.info(f"Average sentiment for {company_key}: {average_sentiment:.2f}")
            results[company_key] = {
                "avg_score": average_sentiment,
                "news": news_items
            }
        else:
            logging.warning(f"No sentiment scores available for {company_key}")

    save_results_to_json(results)
    save_summary_to_txt(results)
