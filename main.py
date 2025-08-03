import requests
from bs4 import BeautifulSoup
import re
import csv
import time
import argparse


def parse_tenders_automated(base_url, max_tenders=100, tenders_per_page=20):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    all_tenders = []
    estimated_pages = (max_tenders + tenders_per_page - 1) // tenders_per_page
    total_pages = estimated_pages + 1

    for page_num in range(1, total_pages + 1):
        url = base_url.format(page_num)

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            tender_articles = soup.find_all('article', class_='tender-row')

            if not tender_articles:
                break

            for article in tender_articles:
                if len(all_tenders) >= max_tenders:
                    return all_tenders

                tender_id = article.get('id', '').strip()

                number_tag = article.find('span', class_='tender__number')
                number_match = re.search(r'№(\d+)', number_tag.get_text()) if number_tag else None
                number = number_match.group(1) if number_match else tender_id

                desc_tag = article.find('a', class_='tender-info__description')
                title = desc_tag.get_text(strip=True) if desc_tag else 'Не указано'
                link = desc_tag['href'] if desc_tag and desc_tag.get('href') else '#'
                full_link = f"https://rostender.info{link}"

                category_tag = article.find('a', class_='list-branches__link')
                category = category_tag.get_text(strip=True) if category_tag else 'Не указана'

                region_tag = article.find('a', class_='tender__region-link')
                region = region_tag.get_text(strip=True) if region_tag else 'Не указан'

                price_tag = article.find('div', class_='starting-price__price')
                price_text = price_tag.get_text(strip=True) if price_tag else ''
                if price_text == '—':
                    desc_text = desc_tag.get_text() if desc_tag else ''
                    price_match = re.search(r'Цена:\s*([\d\s]+руб\.?)', desc_text, re.IGNORECASE)
                    price = price_match.group(1).strip() if price_match else 'Не указана'
                else:
                    price = price_text

                countdown_tag = article.find('span', class_='tender__countdown-text')
                end_date, end_time = '', ''
                if countdown_tag:
                    text = countdown_tag.get_text()
                    date_match = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                    time_match = re.search(r'\d{2}:\d{2}', text)
                    end_date = date_match.group() if date_match else ''
                    end_time = time_match.group() if time_match else ''

                procurement_type = 'Неизвестно'
                if article.find('div', class_='b-44'):
                    procurement_type = '44-ФЗ'
                elif article.find('div', class_='b-223'):
                    procurement_type = '223-ФЗ'
                elif article.find('div', class_='b-commerce'):
                    procurement_type = 'Коммерческий'

                tender = {
                    'id': tender_id,
                    'number': number,
                    'title': title,
                    'link': full_link,
                    'category': category,
                    'region': region,
                    'price': price,
                    'end_date': end_date,
                    'end_time': end_time,
                    'procurement_type': procurement_type
                }
                all_tenders.append(tender)

            if len(tender_articles) < 15:
                break

            if len(all_tenders) >= max_tenders:
                break

        except requests.exceptions.RequestException:
            break
        except Exception:
            break

        time.sleep(1)

    return all_tenders


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=100)
    parser.add_argument('--output', type=str, default='tenders.csv')
    parser.add_argument('--url', type=str, default='https://rostender.info/extsearch?page={}')

    args = parser.parse_args()

    print(f"Запуск парсера...\nМаксимум: {args.max}\nФайл: {args.output}\nURL: {args.url}")

    tenders = parse_tenders_automated(
        base_url=args.url,
        max_tenders=args.max
    )

    if tenders:
        with open(args.output, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=tenders[0].keys())
            writer.writeheader()
            writer.writerows(tenders)
        print(f"\nСохранено {len(tenders)} тендеров в '{args.output}'")
    else:
        print("Ничего не удалось спарсить.")


if __name__ == '__main__':
    main()