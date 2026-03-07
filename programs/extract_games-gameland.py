"""
Цей скрипт збирає інформацію про карткові ігри з простими правилами з сайту gameland.com.ua.
Він обробляє пагінацію, витягує назви ігор та відповідні URL-адреси,
і зберігає результати у файл Markdown під назвою 'GameList-gameland.md'.

Скрипт використовує надійну стратегію аналізу HTML:
1. Він ідентифікує потенційні контейнери продуктів за допомогою загального CSS-селектора.
2. Він фільтрує ці контейнери, перевіряючи наявність ціни ('грн'),
   забезпечуючи обробку лише фактичних товарних позицій.
3. У кожному підтвердженому контейнері продукту він точно витягує головне посилання на гру
   (зазвичай знаходиться в заголовку або має клас 'name'/'title').
4. Він включає 1-секундну затримку між запитами сторінок, щоб уникнути перевантаження сервера.
"""
import requests # Імпорт бібліотеки для виконання HTTP-запитів
from bs4 import BeautifulSoup # Імпорт бібліотеки для парсингу HTML
import re # Імпорт модуля для роботи з регулярними виразами
import time # Імпорт модуля для роботи з часом (для затримки)

def extract_card_games_paginated():
    # Базова URL-адреса для пошуку карткових ігор з простими правилами
    base_search_url = "https://gameland.com.ua/katalog/search/filter/parent=1183;presence=1/?q=%D0%BA%D0%B0%D1%80%D1%82%D0%BA%D0%BE%D0%B2%D1%96%20%D1%96%D0%B3%D1%80%D0%B8%20%D0%BF%D1%80%D0%BE%D1%81%D1%82%D1%96%20%D0%BF%D1%80%D0%B0%D0%B2%D0%B8%D0%BB%D0%B0"
    all_games = [] # Список для зберігання всіх знайдених ігор
    page_number = 1 # Початковий номер сторінки
    
    # Заголовки для HTTP-запиту, щоб імітувати браузер
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'uk-UA,uk;q=0.5',
    }
    
    # Цикл для обробки сторінок з пагінацією
    while True:
        # Формування URL для поточної сторінки
        if page_number == 1:
            url = base_search_url # Для першої сторінки використовуємо базовий URL
        else:
            # Для наступних сторінок вставляємо параметр 'page=X;' у URL
            parts = base_search_url.split('/filter/')
            if len(parts) == 2:
                url = f"{parts[0]}/filter/page={page_number};{parts[1]}"
            else:
                # Запасний варіант, якщо структура URL несподівано зміниться
                print(f"Попередження: Неочікувана структура URL для пагінації: {base_search_url}")
                url = f"{base_search_url}&page={page_number}" # Спроба додати як параметр запиту
            
        print(f"Обробка сторінки {page_number}: {url}")
        
        try:
            # Виконання HTTP-запиту до сторінки
            response = requests.get(url, headers=headers)
            print(f"Статус сторінки: {response.status_code}")
            
            # Зупинка, якщо отримано не-200 статус (наприклад, 404 Not Found)
            if response.status_code != 200:
                print("Зупинка: Отримано статус, відмінний від 200.")
                break

            # Парсинг HTML-вмісту сторінки
            soup = BeautifulSoup(response.content, 'html.parser')
            games_found_on_page = 0 # Лічильник нових ігор, знайдених на поточній сторінці
            
            # Остаточна стратегія:
            # 1. Знайти всі потенційні контейнери продуктів за допомогою загального селектора.
            # Цей селектор шукає будь-який елемент, у якого в атрибуті 'class' є підрядок "product".
            potential_containers = soup.select('[class*="product"]')
            print(f"Знайдено {len(potential_containers)} потенційних контейнерів продуктів.")

            # 2. Відфільтрувати контейнери, перевіряючи наявність ціни ('грн').
            # Це допомагає відсіяти елементи, які не є фактичними товарами (наприклад, категорії, аксесуари).
            product_containers = [c for c in potential_containers if 'грн' in c.get_text()]
            print(f"Відфільтровано до {len(product_containers)} контейнерів з ціною.")

            # Обробка кожного знайденого контейнера продукту
            for container in product_containers:
                link_tag = None # Змінна для зберігання посилання на продукт
                
                # Спроба знайти посилання всередині заголовка (h3, h4) або div з класом 'name'/'title'.
                # Це типові місця для основного посилання на товар.
                heading = container.find(['h3', 'h4', 'div'], class_=re.compile(r'name|title', re.I))
                if heading:
                    link_tag = heading.find('a') # Знайти посилання всередині заголовка
                
                # Якщо посилання не знайдено в заголовку, спробувати знайти його безпосередньо
                # за класом 'name' або 'title'.
                if not link_tag:
                    link_tag = container.find('a', class_=re.compile(r'name|title', re.I))

                # Якщо посилання все ще не знайдено, це не стандартна картка продукту, тому пропускаємо її.
                if not link_tag:
                    continue

                href = link_tag.get('href') # Отримати атрибут href посилання
                text = link_tag.get_text().strip() # Отримати текст посилання та очистити його

                # Перевірка на наявність href та тексту
                if not (href and text):
                    continue

                # Формування повної URL-адреси (абсолютної або відносної)
                if href.startswith('http'):
                    full_link = href
                else:
                    full_link = 'https://gameland.com.ua' + href

                # 3. Фінальна перевірка на дублікати та додавання гри до списку
                if not any(game['link'] == full_link for game in all_games):
                    all_games.append({
                        'title': text,
                        'link': full_link
                    })
                    games_found_on_page += 1 # Збільшення лічильника нових ігор

            # Перевірка, чи були знайдені нові ігри на поточній сторінці
            if games_found_on_page == 0:
                print(f"Зупинка: Нових ігор на цій сторінці не знайдено.")
                break # Зупинити цикл, якщо нових ігор немає
            else:
                print(f"Ігор додано з цієї сторінки: {games_found_on_page}")

        except requests.RequestException as e:
            # Обробка помилок HTTP-запитів
            print(f"Помилка при отриманні сторінки: {e}")
            break # Зупинити цикл при помилці
        
        print("Очікування 1 секунди перед наступною сторінкою...")
        time.sleep(1) # Затримка на 1 секунду для уникнення перевантаження сервера
        page_number += 1 # Перехід до наступної сторінки

    # Збереження результатів у файл Markdown
    output_filename = 'GameList-gameland.md'
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write("# Список карткових ігор із простими правилами з gameland.com.ua\n\n")
        f.write("| N | Назва гри | Посилання на сторінку з описом гри |\n")
        f.write("|---|-----------|------------------------|\n")
        
        # Сортування знайдених ігор за назвою перед записом
        sorted_games = sorted(all_games, key=lambda x: x['title'])
        
        # Запис кожної гри у форматі Markdown-таблиці
        for i, game in enumerate(sorted_games, 1):
            clean_title = re.sub(r'\s+', ' ', game['title']).strip() # Очищення назви від зайвих пробілів
            f.write(f"| {i} | {clean_title} | {game['link']} |\n")
    
    print(f"\nВсього знайдено унікальних ігор: {len(all_games)}")
    print(f"Результати збережено у {output_filename}")

# Точка входу в скрипт
if __name__ == "__main__":
    extract_card_games_paginated()
