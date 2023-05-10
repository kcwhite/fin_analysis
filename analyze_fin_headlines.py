import grequests
import requests
from bs4 import BeautifulSoup
# noinspection PyPackageRequirements
from googlesearch import search
from textblob import TextBlob
import yfinance as yf
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def read_company_names(file_path):
    logging.info(f"Reading company names from file: {file_path}")
    with open(file_path, 'r') as file:
        company_names = [line.strip() for line in file]
    return company_names


def get_ticker_symbol(company_name):
    logging.info(f"Fetching ticker symbol for {company_name}")
    try:
        ticker = yf.Ticker(company_name).info['symbol']
    except Exception as e:
        logging.error(f"Error while fetching ticker symbol for {company_name}: {e}")
        ticker = None
    return ticker


def read_file(file_path):
    with open(file_path, 'r') as file:
        lines = [line.strip() for line in file]
    return lines


def scrape_content(url, headers):
    content = []
    try:
        response = requests.get(url, headers=headers)
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


def request_content(url, headers):
    return grequests.get(url, headers=headers)


def analyze_sentiment(text):
    analysis = TextBlob(text)
    sentiment_score = (analysis.sentiment.polarity + 1) * 5
    return sentiment_score


def predict_stock_trend(company_name, ticker_symbol, news_websites, headers):
    query = f"{company_name}"
    if ticker_symbol:
        query += f" {ticker_symbol}"
    query += " stock news "
    query += " OR ".join([f"site:{website}" for website in news_websites])
    urls = [j for j in search(query, num_results=10)]
    rs = (request_content(url, headers) for url in urls)
    responses = grequests.map(rs)

    content_list = [scrape_content(response.url, headers) for response in responses if response]
    sentiment_scores = [analyze_sentiment(content) for content in content_list]

    news_items = [
        {
            "website": response.url,
            "content": content,
            "score": score
        }
        for response, content, score in zip(responses, content_list, sentiment_scores) if response
    ]

    if sentiment_scores:
        return sum(sentiment_scores) / len(sentiment_scores), news_items
    else:
        return None, news_items


def save_results_to_json(results, file_name='results.json'):
    with open(file_name, 'w') as f:
        json.dump(results, f, indent=2)


def save_summary_to_txt(results, file_name='summary.txt'):
    with open(file_name, 'w') as f:
        for company, data in results.items():
            f.write(f"{company}: {data['avg_score']:.2f}\n")


if __name__ == "__main__":
    company_file_path = 'companies.txt'
    news_websites_file_path = 'news_websites.txt'

    company_names = read_file(company_file_path)
    news_websites = read_file(news_websites_file_path)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    results = {}

    for company_name in company_names:
        ticker_symbol = get_ticker_symbol(company_name)
        company_key = f"{company_name}" + (f" ({ticker_symbol})" if ticker_symbol else "")

        logging.info(f"Analyzing sentiment for {company_key}")

        # Update predict_stock_trend function to return content_list and sentiment_scores as well
        average_sentiment, news_items = predict_stock_trend(company_name, ticker_symbol, news_websites, headers)

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

