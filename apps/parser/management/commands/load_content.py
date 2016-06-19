from django.core.management.base import BaseCommand
from django.utils.html import strip_tags
from apps.parser.core import ContentParser
from urllib.parse import urljoin
import sys


class KedemRuParser(ContentParser):
    def _parse_html(self, html):
        recipe_schema = {
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

        for n in html.findAll('h1', {'class': 'h1', 'itemprop': 'name'}):
            recipe_schema['name'] = n.text.strip().capitalize()

        for i in html.findAll('div', {'class': 'ringlist', 'itemprop': 'ingredients'}):
            recipe_schema['ingredients'].append(strip_tags(i.text.strip().capitalize()))

        for ri in html.findAll('div', {'class': 'rtext', 'itemprop': 'recipeInstructions'}):
            sections = []
            for par in ri.findAll('p'):
                text = strip_tags(par.text.strip())
                src = None

                for sec_img in par.findAll('img'):
                    src = sec_img['src']

                if src:
                    sections.append('<img alt="" src="%s">' % urljoin(self._site, src))
                elif text:
                    sections.append('<p>%s</p>' % text)

            recipe_schema['recipeInstructions'] = sections

        for img in html.findAll('img', {'itemprop': 'image'}):
            recipe_schema['resultPhoto'] = urljoin(self._site, img['src'])

        for p in html.findAll('div', {'class': 'path'}):
            for a in p.findAll('a', {'class': 'pathlink'}):
                txt = strip_tags(a.text.strip())
                if txt not in ('Kedem.ru', 'Рецепты'):
                    recipe_schema['category'].append(txt)

        return recipe_schema if recipe_schema['name'] and recipe_schema['ingredients'] else None



class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        parser = KedemRuParser()
        parser.parse()
        print('Done')