from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.conf import settings

from urllib.parse import urlparse, urljoin
from bs4 import BeautifulStoneSoup as Soup
from abc import ABCMeta, abstractmethod
import urllib.request
import time
import json
import uuid
import re
import os


class UrlParser(object):
    '''
    Класс ищет на сайте все адреса, соответствующие регулярному выражению
    и сохраняет их в файле.
    Имеет единственный публичный метод parse, возвращающий путь к файлу с урлами.
    Использует настройки парсера:
        PARSER__URL_SOURCE
        PARSER__SITEMAP_URL
        PARSER__CELL_HOMEPAGE
        PARSER__RECIPE_URL_TEMPLATE
    '''

    def __init__(self):
        # URL-ы рецептов
        self._urls = set()

        # Все обнаруженные на сайте адреса. Применяется при парсинге html
        self._finds = set()

        # Обработанные адреса. Применяется при парсинге html
        self._processed = set()

        #Интервал в секундах между парсингом html страниц. Целое число.
        self.sleep_time = 1

        # Валидаторы
        self._recipe_validator = URLValidator(regex=settings.PARSER__RECIPE_URL_TEMPLATE)
        self._url_validator = URLValidator()

        self.json_file_path = None

    def parse(self):
        '''
        Метод формирует JSON список url с рецептами сайта и
        сохраняет его в MEDIA_ROOT/parser/source.js.
        В зависимости от настроек анализирует карту сайта или же
        парсит html-страницы.

        '''

        # Парсинг по карте сайта
        if hasattr(settings, 'PARSER__URL_SOURCE') and settings.PARSER__URL_SOURCE == 'sitemap':

            xml = None

            if not hasattr(settings, 'PARSER__SITEMAP_URL') or not settings.PARSER__SITEMAP_URL:
                print('PARSER__SITEMAP_URL is not defined')
            else:
                try:
                    with urllib.request.urlopen(settings.PARSER__SITEMAP_URL) as response:
                        xml = response.read()
                except Exception:
                    xml = None

            if xml:
                sitemap = Soup(xml)
                urls = sitemap.findAll('url')
                for u in urls:
                    loc = u.find('loc').string
                    self._add_location(loc)
        else:
            # Парсинг по тегам html-страниц
            if not hasattr(settings, 'PARSER__CELL_HOMEPAGE') or not settings.PARSER__CELL_HOMEPAGE:
                print('PARSER__CELL_HOMEPAGE is not defined')
                return False

            # Счетчик рекурсивных вызовов метода _parse_html
            self._recursion_counter = 0

            self._parse_html(settings.PARSER__CELL_HOMEPAGE)

        self._save()

        return self.json_file_path

    def _add_location(self, location):
        '''
        Метод добавляет локацию в self._urls если она
        соответствует регулярному выражению.

        '''

        try:
            self._recipe_validator(location)
            self._urls.add(location)
        except ValidationError:
            pass

    def _save(self):
        '''
        Метод сохраняет сериализованный в JSON список урлов с рецептами.
        Файл сохраняется в MEDIA_ROOT/parser/source.js.

        '''

        if self.json_file_path is None:
            directory = os.path.join(settings.MEDIA_ROOT, 'parser')

            if not os.path.exists(directory):
                os.makedirs(directory)

            self.json_file_path = os.path.join(directory, 'source.js')

        if os.path.exists(self.json_file_path):
            os.remove(self.json_file_path)

        with open(self.json_file_path, 'w') as outfile:
            json.dump(list(self._urls), outfile)

    def _build_link(self, url, location_parts):
        '''
        Метод формирует и возвращает ссылку приведенную к абсолютной
        или None, если ссылка некоректна.

        '''

        href = None

        scheme = location_parts.scheme
        domain = location_parts.netloc
        location = location_parts.path
        site = '%s://%s' % (scheme, domain)

        if url:
            if url[0] == '/':
                # Ссылка относительно корня сайта
                href = urljoin(site, url)
            elif url[:len(site)] == site:
                # Абсолютная ссылка
                href = url
            elif url[:len(domain)] == domain:
                # Ссылка без протокола
                href = '%s://%s' % (scheme, url)
            elif '://' in url:
                # Ссылка на другой домен или протокол
                href = None
            elif 'javascript:' in url:
                # JS
                href = None
            elif url[0] == '#':
                # Якорь
                href = None
            elif 'mailto:' in url:
                href = None
            else:
                # Ссылка относительно текущего документа (или ссылка с GET вида ?...)
                doc = urljoin(site, location)
                href = urljoin(doc, url)

        return href

    def _parse_html(self, url):
        '''
        Метод загружает страницу из url и обрабатывает все ссылки на ней присутствующие.
        Рекурсивно вызывает самого себя для первой из еще не обработанных ссылок, т.о.
        парсится весь сайт.

        '''

        html = None
        page_content = None

        self._processed.add(url)
        self._recursion_counter += 1

        try:
            with urllib.request.urlopen(url) as response:
                html = response.read()
        except Exception:
            html = None
            print('Unable to load url %s' % url)

        if html:
            try:
                page_content = Soup(html)
            except Exception:
                page_content = None

        if page_content:
            stop_list = ('#', '', '/')

            for a in page_content.find_all('a', href=True):
                if a['href'] not in stop_list:
                    href = self._build_link(url=a['href'], location_parts=urlparse(url))
                    if href:
                        try:
                            self._url_validator(href)
                        except ValidationError:
                            print('%s is not valid url' % href)
                        else:
                            self._finds.add(href)

            self._add_location(url)

        unprocessed = self._finds - self._processed

        print('Всего страниц: %s. Обработано страниц: %s. Найдено рецептов: %s. Последний URL: %s' %
            (len(self._finds), len(self._processed), len(self._urls), url))

        # На каждом 20-ом вызове данного метода сохраняем self._urls
        if self._recursion_counter % 20:
            self._save()
            self._recursion_counter = 0

        if unprocessed:
            if self.sleep_time > 0:
                time.sleep(self.sleep_time)

            next_url = list(unprocessed)[0]
            self._parse_html(next_url)


class ContentParser(object):
    __metaclass__ = ABCMeta

    '''
    Класс сериализует рецепты с загружаемых страниц в виде json-файлов.

    Для использования необходимо переопределить в потомке абстрактный метод _parse_html
    в соответствии с содержимым карточки рецепта конкретного сайта с рецептами.

    Единственный публичный метод parse итеративно загружает страницы из json-файла,
    обрабатывает их с помощью метода _parse_html и сохраняет в виде json файла.

    '''

    def __init__(self, file_path=None):
        '''
        file_path -- абсолютный путь к JSON файлу со списком урлов.
        Если file_path не определен, то метод попытается загрузить
        данные из MEDIA_ROOT/parser/source.js.

        '''

        if file_path is None:
            directory = os.path.join(settings.MEDIA_ROOT, 'parser')
            file_path = os.path.join(directory, 'source.js')

        if not os.path.exists(file_path):
            raise Exception('JSON file not found')

        with open(file_path) as input_file:
            try:
                urls = json.load(input_file)
            except Exception:
                urls = []

        self._urls = urls
        self._urls_length = len(self._urls)
        self._url_validator = URLValidator()
        self._site = None

        #Интервал в секундах между парсингом html страниц. Целое число.
        self.sleep_time = 1


    def parse(self):
        '''
        Каждая из страниц self._urls парсится методом _parse_html,
        если результат, возвращенный _parse_html, отличен от None,
        то результат сохраняется методом _save_recipe.
        '''

        for url in self._urls:
            html = None

            if not hasattr(self, '_recipe_count'):
                self._recipe_count = 1
            else:
                self._recipe_count += 1

            try:
                self._url_validator(url)
            except ValidationError:
                print('%s is not valid url' % url)
            else:
                try:
                    location_parts=urlparse(url)
                    self._site = '%s://%s' % (location_parts.scheme, location_parts.netloc)

                    with urllib.request.urlopen(url) as response:
                        html = Soup(response.read())
                except Exception:
                    html = None

            if html:
                recipe = self._parse_html(html=html)
                if recipe:
                    self._save_recipe(recipe=recipe)

            print('Всего загружено: %s\%s' % (self._recipe_count, self._urls_length))

            if self.sleep_time > 0:
                time.sleep(self.sleep_time)

    @abstractmethod
    def _parse_html(self, html):
        '''
        Метод принимает bs4-объект html страницы.
        Метод должен возвратить None или словарь описывающий рецепт вида:
        {
            'name': None,
            'summary': None,
            'ingredients': [],
            'image': [],
            'recipeInstructions': None,
            'cookTime': None,
            'recipeYield': None,
            'resultPhoto': None,
            'category': [],
        }

        Все ключи словаря, кроме category, должны быть заполнены в соответствии
        с логикой микроразметки Яндекс Рецептов.
        Ключ category -- структура товара в каталоге целевого сайта

        '''
        raise NotImplementedError('Abstract method raise')

    def _save_recipe(self, recipe):
        '''
        Сохранение словара с рецептом в json-файл.
        Файл размещается в в MEDIA_ROOT/parser/recipes/

        '''

        recipe_id = uuid.uuid4().hex
        js_recipe = json.dumps(recipe)

        parser_directory = os.path.join(settings.MEDIA_ROOT, 'parser')
        recipe_dir = os.path.join(parser_directory, 'recipes')

        if not os.path.exists(recipe_dir):
            os.makedirs(recipe_dir)

        recipe_fullpath = os.path.join(recipe_dir, '%s.js' % recipe_id)

        if os.path.exists(recipe_fullpath):
            os.remove(recipe_fullpath)

        with open(recipe_fullpath, 'w') as rf:
            rf.write(js_recipe)