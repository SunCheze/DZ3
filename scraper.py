import requests
from bs4 import BeautifulSoup
import re
import time
from pathlib import Path
import schedule
from datetime import datetime
import pathlib



def get_book_data(book_url: str) -> dict:
    """
    Извлекает данные о книге с страницы интернет-магазина.

    Args:
        book_url (str): URL страницы книги (например,
                   http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html)

    Returns:
        dict: Словарь с полями:
            - title (str): название книги
            - price (float): цена в фунтах (число)
            - rating (int): рейтинг (0–5)
            - in_stock (int): количество в наличии
            - description (str): описание
            - product_info (dict): дополнительные характеристики из таблицы Product Information
                (UPC, Product Type, Price (excl. tax), Price (incl. tax), Tax, Availability, Number of reviews)
    """
    try:
        # Выполняем GET-запрос
        response = requests.get(book_url, timeout=10)
        response.raise_for_status()  # Проверяем статус ответа

        # Парсим HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Извлекаем название
        title = soup.find('h1').get_text(strip=True)

        # Извлекаем цену (в формате £12.99 → 12.99)
        price_text = soup.find('p', class_='price_color').get_text(strip=True)
        price = float(price_text.replace('£', ''))

        # Извлекаем рейтинг (класс типа 'star-rating Three')
        rating_elem = soup.find('p', class_='star-rating')
        rating_classes = rating_elem['class']
        rating_words = [c for c in rating_classes if c != 'star-rating']
        rating_word = rating_words[0] if rating_words else 'Zero'

        rating_map = {
            'Zero': 0,
            'One': 1,
            'Two': 2,
            'Three': 3,
            'Four': 4,
            'Five': 5
        }
        rating = rating_map.get(rating_word, 0)

        # Извлекаем количество в наличии (например, 'In stock (18 available)')
        stock_text = soup.find('p', class_='instock availability').get_text(strip=True)

        # Ищем число в скобках
        stock_match = re.search(r'\((\d+)\s*available\)', stock_text)
        in_stock = int(stock_match.group(1)) if stock_match else 0

        # Извлекаем описание (раздел после <h2>Product Description</h2>)
        description_elem = soup.find('div', id='product_description')
        if description_elem and description_elem.find_next_sibling('p'):
            description = description_elem.find_next_sibling('p').get_text(strip=True)
        else:
            description = ''

        # Извлекаем таблицу Product Information
        product_info = {}
        table = soup.find('table', class_='table table-striped')
        if table:
            for row in table.find_all('tr'):
                key = row.find('th').get_text(strip=True)
                value = row.find('td').get_text(strip=True)
                product_info[key] = value

        return {
            'title': title,
            'price': price,
            'rating': rating,
            'in_stock': in_stock,
            'description': description,
            'product_info': product_info
        }

    except requests.RequestException as e:
        print(f"Ошибка при запросе к {book_url}: {e}")
        return {}
    except Exception as e:
        print(f"Неожиданная ошибка при парсинге: {e}")
        return {}


if __name__ == '__main__':
    book_url = "http://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    data = get_book_data(book_url)
    print(data)



def scrape_books(start_page: int = 1, end_page: int = 50, save_to_file: bool = False) -> list:
    """
    Парсит книги со страниц каталога books.toscrape.com.

    Args:
        start_page (int): Номер начальной страницы (по умолчанию 1)
        end_page (int): Номер конечной страницы (по умолчанию 50)
        save_to_file (bool): Флаг сохранения результата в файл books_data.txt

    Returns:
        list: Список словарей с данными о книгах
    """
    all_books = []
    base_url = "http://books.toscrape.com/catalogue/page-{}.html"

    print(f"Начинаем парсинг страниц с {start_page} по {end_page}...")

    for page_num in range(start_page, end_page + 1):
        page_url = base_url.format(page_num)
        print(f"Обрабатываю страницу {page_num}: {page_url}")

        try:
            # Получаем HTML страницы каталога
            response = requests.get(page_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Находим все ссылки на книги на странице
            book_links = soup.find_all('h3')

            for book_link in book_links:
                # Извлекаем относительный URL книги
                relative_url = book_link.find('a')['href']
                # Формируем полный URL
                book_url = f"http://books.toscrape.com/catalogue/{relative_url}"

                # Парсим данные книги
                book_data = get_book_data(book_url)
                if book_data:  # Если данные успешно получены
                    all_books.append(book_data)
                    print(f"  ✓ Добавлена книга: {book_data['title']}")
                else:
                    print(f"  ✗ Не удалось получить данные для книги по URL: {book_url}")

                    # Небольшая задержка, чтобы не перегружать сервер
                    time.sleep(0.1)

        except requests.RequestException as e:
            print(f"Ошибка при загрузке страницы {page_num}: {e} ")
            continue
        except Exception as e:
            print(f"Неожиданная ошибка на странице {page_num}: {e}")
            continue

    print(f"\nПарсинг завершён. Всего собрано {len(all_books)} книг.")

    # Сохранение в файл, если флаг установлен
    if save_to_file:
        file_path = Path("books_scraper/books_data.txt")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for i, book in enumerate(all_books, 1):
                    f.write(f"--- Книга {i} ---\n")
                    for key, value in book.items():
                        if key == "product_info":
                            f.write("product_info:\n")
                            for k, v in value.items():
                                f.write(f"  {k}: {v}\n")
                        else:
                            f.write(f"{key}: {value}\n")
                    f.write("\n")
            print(f"Данные сохранены в файл: {file_path.resolve()}")
        except IOError as e:
            print(f"Ошибка при сохранении файла: {e}")

    return all_books


# Пример использования
if __name__ == "__main__":
    # Парсим первые 3 страницы и сохраняем результат в файл
    books = scrape_books(start_page=1, end_page=3, save_to_file=True)
    # Или без сохранения в файл
    # books = scrape_books(start_page=1, end_page=2, save_to_file=False)



# task 3
def daily_scrape():
    """Функция для ежедневного запуска парсинга и сохранения данных."""
    print(f"[{datetime.now()}] Запуск ежедневного парсинга...")

    # Парсим данные
    books = scrape_books(start_page=1, end_page=3)  # Для примера берём 3 страницы

    # Формируем имя файла с датой
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"books_data_{timestamp}.txt"
    filepath = pathlib.Path(filename)

    # Сохраняем в файл
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"Данные собраны: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего книг: {len(books)}\n\n")

            for i, book in enumerate(books, 1):
                f.write(f"--- Книга {i} ---\n")
                for key, value in book.items():
                    if key == "product_info":
                        f.write("product_info:\n")
                        for k, v in value.items():
                            f.write(f"{k}: {v}\n")
                    else:
                        f.write(f"{key}: {value}\n")
                        f.write("\n")
                        print(f"[{datetime.now()}] Данные сохранены в {filepath}")
    except IOError as e:
        print(f"[{datetime.now()}] Ошибка при сохранении файла: {e}")


def main():
    """Основная функция с планировщиком."""
    # Настраиваем расписание
    schedule.every().day.at("19:00").do(daily_scrape)
    # Для тестирования можно добавить запуск в ближайшее время:
    # schedule.every().minutes.do(daily_scrape)  # Каждые минуты (для теста)

    print("Планировщик запущен. Ожидание времени запуска...")
    print("Для выхода Ctrl+C")

    # Бесконечный цикл с проверкой расписания
    while True:
        schedule.run_pending()  # Проверяем, есть ли запланированные задачи
        time.sleep(30)  # Проверяем каждые 30 секунд (оптимальный интервал)


if __name__ == "__main__":
    main()