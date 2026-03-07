"""
Цей скрипт збирає інформацію про карткові ігри з сайту planeta-igr.com.
Він використовує Playwright для обробки динамічного контенту, завантаженого за допомогою JavaScript.

Скрипт виконує наступні кроки:
1. Запускає браузер за допомогою Playwright.
2. Переходить на кожну сторінку з результатами пошуку.
3. Очікує, доки динамічний контент (сітка товарів) не буде завантажений.
4. Отримує повний HTML сторінки та передає його в BeautifulSoup.
5. Парсить HTML для вилучення назв ігор та посилань.
6. Зберігає результати у файл Markdown 'GameList-planetaigr.md'.
"""
import time
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def extract_planeta_igr_games():
    # Базова URL-адреса для пошуку карткових ігор
    base_search_url = "https://planeta-igr.com/ua/katalog/nastolnie-igri/tipi-igr/izuchaem-anglijskij/"
    all_games = [] # Список для зберігання всіх знайдених ігор
    page_number = 1 # Початковий номер сторінки

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # Запуск браузера (headless=True для фонового режиму)
        page = browser.new_page()

        # Цикл для обробки сторінок з пагінацією
        while True:
            url = f"{base_search_url}&page={page_number}"
            print(f"Processing page {page_number}: {url}")

            try:
                # Перехід на сторінку та очікування завершення мережевої активності
                response = page.goto(url, wait_until='networkidle', timeout=20000)
                print(f"Page status: {response.status}")

                if response.status != 200:
                    print("Stopping: Got status different from 200.")
                    break

                # Отримання HTML-вмісту сторінки ПІСЛЯ виконання JavaScript
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                games_found_on_page = 0

                # Пошук посилань на ігри за правильним селектором
                # За допомогою аналізу HTML було виявлено, що ігри мають структуру:
                # <div class="name "><a href="...">Назва гри</a></div>
                # Попередні селектори .product-layout та a.name не відповідали актуальній структурі
                game_links = soup.select('.name a')
                print(f"Found {len(game_links)} game links.")

                for link_tag in game_links:
                    href = link_tag.get('href')
                    text = link_tag.get_text().strip()

                    if not (href and text):
                        continue

                    # Перевірка на дублікати та додавання до списку
                    if not any(game['link'] == href for game in all_games):
                        all_games.append({'title': text, 'link': href})
                        games_found_on_page += 1

                if games_found_on_page == 0:
                    print("Stopping: No new games found on this page.")
                    break
                else:
                    print(f"Games added from this page: {games_found_on_page}")

            except Exception as e:
                print(f"Error processing page {page_number}: {e}")
                break
            
            print("Waiting 1 second before next page...")
            time.sleep(1)
            page_number += 1

        browser.close() # Закриття браузера

    # Збереження результатів у файл Markdown
    output_filename = '../Docs/GameList-planetaigr-ForeignLang.md'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write("# Список карткових ігор з planeta-igr.com\n\n")
        f.write("| N | Назва гри | Посилання на сторінку з описом гри |\n")
        f.write("|---|-----------|------------------------|\n")
        
        # Зберігаємо ігри в порядку отримання, щоб зберігти хронологію зі сторінок
        # та зберігти послідовність, в якій вони відображаються на сайті
        for i, game in enumerate(all_games, 1):
            clean_title = re.sub(r'\s+', ' ', game['title']).strip()
            f.write(f"| {i} | {clean_title} | {game['link']} |\n")
    
    print(f"\nTotal unique games found: {len(all_games)}")
    print(f"Results saved to {output_filename}")

if __name__ == "__main__":
    extract_planeta_igr_games()