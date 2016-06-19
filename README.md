# RecipeParser

Настройки
------------

Файл RecipeParser/parser_settings.py

PARSER__URL_SOURCE -- определяет источник получения урлов страниц сайта. Если значением является "sitemap", то, соответственно, источником является файл sitemap.xml, в противном случае парсер будет рекурсивно искать ссылки на всех страницах сайта.

PARSER__RECIPE_URL_TEMPLATE -- регулярное выражение, для URI карточки рецепта конкретного сайта.

PARSER__SITEMAP_URL -- абсолютный адрес файла sitemap.xml. Используется только если PARSER__URL_SOURCE == 'sitemap'

PARSER__CELL_HOMEPAGE -- абсолютный адрес главной страницы сайта. Используется если PARSER__SITEMAP_URL != 'sitemap'


Архитектура
------------

Ядром парсера является два класса:
    * UrlParser (apps.parser.core.UrlParser)
    * ContentParser (apps.parser.core.ContentParser)

Класс UrlParser формирует json-список всех урлов сайта, которые соответсвуют регулярному выражению PARSER__RECIPE_URL_TEMPLATE. Ссылки, в зависимости от настроек, либо извлекаются из карты сайта (быстро), либо же парсится весь сайт и ссылки извлекаются из контента и проводятся к абсолютным (долго). Список сохраняется в MEDIA_ROOT/parser/source.js.
Для использования класс UrlParser нуждается в настройках (RecipeParser/parser_settings.py).
Единственный публичный метод parse().

Класс ContentParser является абстрактнымм, соответственно для парсинга конкретного сайта должен быть создан класс-потомок. В потомке необходимо переопределить метод _parse_html(), который принимает контент страницы с карточкой рецепта (в виде экземпляра BeautifulSoup4) и должен возвратить словарь с данными, пригодными для сериализации в json. В словаре могут присутствовать следующие ключи:
[name, summary, ingredients, image, recipeInstructions, cookTime, recipeYield, resultPhoto, category]
Все ключи словаря, кроме category, должны быть заполнены в соответствии с логикой микроразметки Яндекс Рецептов.
Ключ category -- структура товара в каталоге целевого сайта. Ссылка на изображения должны быть приведены к абсолютному виду.
Единственный публичный метод класса -- parse().
Каждый из рецептом сохраняется как отдельный файл в директории MEDIA_ROOT/parser/recipes/


Использование
------------

Пример использования UrlParser -- комманда get_urls (apps.parser.management.commands.get_urls) По умолчанию парсер настроен на сайт kedem.ru.
Пример использования ContentParser (точнее его потомка) -- комманда load_content (apps.parser.management.commands.load_content). Тестовый потомок написан для парсинга kedem.ru.

Зависимости
------------

* py3k
* Django
* beautifulsoup4
* psycopg2
* lxml

Установка системных библиотек для работы lxml в Дебиане и его форках -- http://lxml.de/installation.html


Установка
------------

    * Переименовать файл RecipeParser/local_settings.py.dist в RecipeParser/local_settings.py и настроить подключение к БД
    * В виртуальном окружении "pip -r requirements.txt"