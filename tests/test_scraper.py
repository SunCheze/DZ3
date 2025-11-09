import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from DZ3 import get_book_data, scrape_books

# Добавляем родительскую директорию в PATH
sys.path.insert(0, str(Path(__file__).parent.parent))




# Тест 1: Проверка структуры и ключей словаря от get_book_data
def test_get_book_data_returns_dict_with_correct_keys():
    # Мокируем запрос и ответ
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <h1>Test Book Title</h1>
        <p class="price_color">£10.00</p>
        <p class="star-rating Three"></p>
        <p class="instock availability">In stock (5 available)</p>
        <div id="product_description"><p>This is a test description.</p></div>
        <table class="table table-striped">
            <tr><th>UPC</th><td>123456789</td></tr>
            <tr><th>Product Type</th><td>Book</td></tr>
        </table>
    </html>
    """

    with patch('requests.get', return_value=mock_response):
        result = get_book_data("http://test.com")

    # Проверяем, что результат — словарь
    assert isinstance(result, dict)

    # Проверяем наличие всех ожидаемых ключей
    expected_keys = ['title', 'price', 'rating', 'in_stock', 'description', 'product_info']
    for key in expected_keys:
        assert key in result

    # Проверяем типы значений
    assert isinstance(result['title'], str)
    assert isinstance(result['price'], float)
    assert isinstance(result['rating'], int)
    assert isinstance(result['in_stock'], int)
    assert isinstance(result['description'], str)
    assert isinstance(result['product_info'], dict)


# Тест 2: Проверка корректности значений отдельных полей
def test_get_book_data_correct_field_values():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = """
    <html>
        <h1>My Test Book</h1>
        <p class="price_color">£25.50</p>
        <p class="star-rating Five"></p>
        <p class="instock availability">In stock (10 available)</p>
        <div id="product_description"><p>Awesome book about testing.</p></div>
        <table class="table table-striped">
            <tr><th>UPC</th><td>987654321</td></tr>
        </table>
    </html>
    """

    with patch('requests.get', return_value=mock_response):
        result = get_book_data("http://test.com")

    assert result['title'] == "My Test Book"
    assert result['price'] == 25.50
    assert result['rating'] == 5
    assert result['in_stock'] == 10
    assert result['description'] == "Awesome book about testing."
    assert result['product_info']['UPC'] == "987654321"


# Тест 3: Проверка scrape_books — количество книг соответствует ожиданиям
@patch('DZ3.get_book_data')
@patch('requests.get')
def test_scrape_books_returns_expected_number_of_books(mock_requests_get, mock_get_book_data):
    # Мокируем ответ сервера для страницы каталога
    mock_catalog_response = MagicMock()
    mock_catalog_response.status_code = 200
    mock_catalog_response.text = """
    <html>
        <section>
            <ol>
                <li><h3><a href="book1.html"></a></h3></li>
                <li><h3><a href="book2.html"></a></h3></li>
                <li><h3><a href="book3.html"></a></h3></li>
            </ol>
        </section>
    </html>
    """
    mock_requests_get.return_value = mock_catalog_response

    # Мокируем get_book_data для каждой книги
    mock_get_book_data.return_value = {
        'title': 'Mock Book',
        'price': 0.0,
        'rating': 0,
        'in_stock': 0,
        'description': '',
        'product_info': {}
    }

    # Вызываем функцию (парсим 1 страницу с 3 книгами)
    books = scrape_books(start_page=1, end_page=1)

    # Проверяем количество книг
    assert len(books) == 3

    # Проверяем, что каждая запись — словарь
    for book in books:
        assert isinstance(book, dict)
