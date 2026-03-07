"""
Цей скрипт збирає детальний опис карткових ігор з сайту planeta-igr.com.
Він читає список ігор з файлу GameList-planetaigr-ForeignLang.md,
переходить на кожну сторінку гри та збирає інформацію про неї.

Скрипт виконує наступні кроки:
1. Читає список ігор з Markdown-файлу.
2. Для кожної гри переходить на її сторінку.
3. Збирає опис, характеристики та іншу інформацію.
4. Зберігає результати у файл Markdown 'GameDescr-planetaigr-ForeignLang.md'.
"""
import re
import time
import sys
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Встановлюємо UTF-8 кодування для виводу в консоль
sys.stdout.reconfigure(encoding='utf-8')


def read_games_list(filepath):
    """Читає список ігор з Markdown-файлу."""
    games = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        for line in lines:
            # Пропускаємо заголовок та розділювач таблиці
            if line.startswith('| N |') or line.startswith('|---|'):
                continue
            
            # Парсить рядки таблиці
            match = re.match(r'\|\s*\d+\s*\|\s*(.+?)\s*\|\s*(https?://.+?)\s*\|', line)
            if match:
                title = match.group(1).strip()
                url = match.group(2).strip()
                games.append({'title': title, 'url': url})
        
        print(f"Read {len(games)} games from {filepath}")
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        return []
    
    return games


def extract_game_description(url, page):
    """Отримує опис гри зі сторінки."""
    try:
        response = page.goto(url, wait_until='domcontentloaded', timeout=60000)
        
        # Додаткове очікування завантаження контенту
        page.wait_for_timeout(3000)
        
        if response.status != 200:
            print(f"  Page status: {response.status} - skipping")
            return None
        
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Збираємо основну інформацію
        description_data = {
            'title': '',
            'description': '',
            'charactersistics': {},
            'price': '',
            'availability': ''
        }
        
        # Отримуємо назву гри (заголовок h1)
        h1 = soup.find('h1')
        if h1:
            description_data['title'] = h1.get_text().strip()
        
        # Отримуємо опис гри
        # Шукаємо блок з описом
        description_div = soup.find('div', {'id': 'tab-description'})
        if not description_div:
            description_div = soup.find('div', class_='product-description')
        if not description_div:
            # Альтернативний пошук - шукаємо текст після заголовка
            description_div = soup.find('div', class_='short-description')
        
        if description_div:
            description_data['description'] = description_div.get_text(' ', strip=True)
        
        # Отримуємо характеристики
        characteristics = {}
        
        # Шукаємо таблицю характеристик
        spec_table = soup.find('table', class_='product-specs')
        if spec_table:
            rows = spec_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    characteristics[key] = value
        
        # Альтернативний пошук характеристик
        if not characteristics:
            # Шукаємо блоки з інформацією про товар
            info_blocks = soup.select('.product-info li, .specs-list li')
            for block in info_blocks:
                text = block.get_text(strip=True)
                if ':' in text:
                    parts = text.split(':', 1)
                    characteristics[parts[0].strip()] = parts[1].strip()
                elif ' - ' in text:
                    parts = text.split(' - ', 1)
                    characteristics[parts[0].strip()] = parts[1].strip()
        
        description_data['characteristics'] = characteristics
        
        # Отримуємо ціну
        price_element = soup.find('span', class_='price')
        if not price_element:
            price_tags = soup.find_all('span', class_=True)
            for tag in price_tags:
                cls = tag.get('class', [])
                if any('price' in str(c).lower() for c in cls):
                    price_element = tag
                    break
        if price_element:
            description_data['price'] = price_element.get_text(strip=True)
        
        # Отримуємо наявність
        availability = soup.find('span', class_='availability')
        if not availability:
            avail_tags = soup.find_all('span', class_=True)
            for tag in avail_tags:
                cls = tag.get('class', [])
                if any('stock' in str(c).lower() or 'availability' in str(c).lower() or 'nal' in str(c).lower() for c in cls):
                    availability = tag
                    break
        if availability:
            description_data['availability'] = availability.get_text(strip=True)
        
        return description_data
        
    except Exception as e:
        print(f"  Error extracting description: {e}")
        return None


def extract_game_descriptions(limit=None, start_index=0):
    """Основна функція для збору описів ігор."""
    # Шлях до файлу зі списком ігор
    input_filepath = '../Docs/GameList-planetaigr-ForeignLang.md'
    
    # Читаємо список ігор
    games = read_games_list(input_filepath)
    
    if not games:
        print("No games to process. Exiting.")
        return
    
    # Пропускаємо ігри до start_index
    if start_index > 0:
        games = games[start_index:]
        print(f"Skipping first {start_index} games, starting from game #{start_index + 1}")
    
    # Обмежуємо кількість ігор для тестування
    if limit:
        games = games[:limit]
        print(f"Processing {limit} games (test mode)")
    else:
        print(f"Processing all {len(games)} games")
    
    all_descriptions = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for i, game in enumerate(games, 1):
            print(f"\n[{i}/{len(games)}] Processing: {game['title']}")
            print(f"  URL: {game['url']}")
            
            description = extract_game_description(game['url'], page)
            
            if description:
                description['original_url'] = game['url']
                all_descriptions.append(description)
                print(f"  Title extracted: {description['title'][:50]}..." if description['title'] else "  No title found")
            else:
                print(f"  Stopping: Could not extract description from this page.")
                break
            
            # Пауза між запитами
            if i < len(games):
                time.sleep(1)
        
        browser.close()
    
    # Зберігаємо результати
    output_filepath = '../Docs/GameDescr-planetaigr-ForeignLang.md'
    save_descriptions(all_descriptions, output_filepath, append=start_index > 0, start_number=start_index + 1)
    
    print(f"\nTotal descriptions collected: {len(all_descriptions)}")
    print(f"Results saved to {output_filepath}")


def save_descriptions(descriptions, filepath, append=False, start_number=1):
    """Зберігає описи ігор у Markdown-файл."""
    mode = 'a' if append else 'w'
    with open(filepath, mode, encoding='utf-8') as f:
        if not append:
            f.write("# Опис карткових ігор з planeta-igr.com\n\n")
            f.write("Зібрано ігор: {}\n\n".format(len(descriptions)))
            f.write("---\n\n")
        
        for i, desc in enumerate(descriptions, start_number):
            f.write(f"## {i}. {desc.get('title', 'Без назви')}\n\n")
            
            if desc.get('original_url'):
                f.write(f"**URL**: [{desc['original_url']}]({desc['original_url']})\n\n")
            
            if desc.get('description'):
                f.write(f"**Опис**: {desc['description']}\n\n")
            
            if desc.get('characteristics'):
                f.write("**Характеристики**:\n\n")
                f.write("| Параметр | Значення |\n")
                f.write("|------------|----------|\n")
                for key, value in desc['characteristics'].items():
                    f.write(f"| {key} | {value} |\n")
                f.write("\n")
            
            if desc.get('price'):
                f.write(f"**Ціна**: {desc['price']}\n\n")
            
            if desc.get('availability'):
                f.write(f"**Наявність**: {desc['availability']}\n\n")
            
            f.write("---\n\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Збір описів ігор з planeta-igr.com')
    parser.add_argument('--start', type=int, default=0, help='Почати з гри № (індекс)')
    parser.add_argument('--limit', type=int, default=None, help='Обмежити кількість ігор')
    args = parser.parse_args()
    
    # Виконуємо збір описів для всіх ігор
    # Для тестування перших 2 ігор: python extract_games-descr-planetaigr.py --limit 2
    # Для продовження з 7-ї гри: python extract_games-descr-planetaigr.py --start 6
    extract_game_descriptions(limit=args.limit, start_index=args.start)
