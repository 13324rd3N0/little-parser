# -*- coding: utf-8 -*-

import os
from lxml import html
import requests
from urllib.parse import urlparse
import configparser

HEADER = ['h1', 'h2', 'h3', 'h4']

SINGLE_HIDE_SYMBOL = [' ', '\n', '→']

DEFAULT_XPATH = ('//p/descendant-or-self::*/ancestor-or-self::* | //p[last()]/preceding::*'
                 '[self::h1 or self::h2 or self::h3 or self::h4]/descendant-or-self::*')

DEFAULT_FILE_NAME = 'index'


class mini_readability(object):

    def __init__(self, url, conf=None):
        self.url = url
        xpath_list = self._pars_conf(conf)
        self.xpath = self._search_xpath(xpath_list)

    def _pars_conf(self, conf=None):
        """
        Функция для парсинга xpath-запросов.
        :param conf: путь до файла конфигурации.
        :return: лист словарей xpath-запросов.
        """
        _config = configparser.ConfigParser()
        config = []
        if conf:
            _config.read(conf)
        for section in _config.sections():
            c = {}
            c['name'] = section
            c['xpath'] = _config.get(section, 'xpath')
            config.append(c)
        return config

    def _search_xpath(self, xpath_list):
        """
        Функция для нахождения правил xpath для конкретной страницы/сайта.
        :param xpath_list: лист словарей с xpath-запросами.
        :return: xpath-запрос по умолчанию или из словаря.
        """
        xpath = DEFAULT_XPATH
        for conf in xpath_list:
            if conf['name'] in self.url:
                xpath = conf['xpath']
        return xpath

    def _get_page(self, url):
        """
        Функция попытки доступа к url.
        :param url: url страницы.
        :return: html код страницы.
        """
        page = None
        r = requests.get(url)
        if r.status_code == 200:
            page = r.text
        return page

    def _end_of_line(self, text):
        """
        Функция проверки конца предложения.
        :param text: проверяемый текст.
        :return: обработанный текст.
        """
        result_str = text
        list_eol_symbol = [".", "!", "?"]
        if text[-1:] in list_eol_symbol:
            result_str += "\n\n "
        return result_str

    def _parse_xpath(self, page, xpath):
        """
        Функция построения DOM дерева.
        :param page: html страница.
        :param xpath: xpath выражение.
        :return: DOM объект (HtmlElements).
        """
        values = None
        doc = html.document_fromstring(page)
        if len(doc):
            values = doc.xpath(xpath)
        return values

    def _parse_str(self, values):
        """
        Функция для преобразования DOM объекта в строку.
        :param values: DOM объект (HtmlElements).
        :return: строка данных.
        """
        raw_str = ''
        if values:
            for v in values:
                # Если таг элемента равен одному из h, то отбиваем пустой строкой.
                if v.tag in HEADER:
                    if v.text:
                        raw_str += v.text
                        if v.tail:
                            raw_str += v.tail
                        raw_str += "\n\n "
                    continue

                # Если таг элемента — ссылка, то проверяем на наличие текста и окончания.
                # Ссылки всё равно могут превышать 80 символов.
                if v.tag == "a":
                    raw_str +="[{}] ".format(v.attrib.get('href',''))
                    # Есть текст и окончание? вероятнее всего это целое предложение, проверяем на конец строки.
                    if v.text and v.tail:
                        sam_str = v.text + v.tail
                        raw_str += self._end_of_line(sam_str)
                    elif v.text and not v.tail:
                        # Возможно предок элемента — заголовок.
                        if v.getparent().tag in HEADER:
                            raw_str += "{}\n\n ".format(v.text)
                        else:
                            raw_str += self._end_of_line(v.text)
                    elif v.tail and not v.text:
                        raw_str += self._end_of_line(v.tail)
                    continue

                # Остальные элементы с текстом.
                # Доработать, на предмет пустого пространства.
                if v.text and v.text not in SINGLE_HIDE_SYMBOL:
                    # Если предок элемента — ссылка, то вероятно это обособленный элемент.
                    if  v.getparent() is not None and v.getparent().tag == 'a':
                        # Если у предка нету текста и окончания, то вероятнее всего,
                        # после элемента необходо отбить строку.
                        if not v.getparent().text and not v.getparent().tail:
                            raw_str += "{}\n\n ".format(v.text)
                    else:
                        raw_str += self._end_of_line(v.text)

        return raw_str

    def _format_str(self, raw_str):
        """
        Функция для форматирования теста.
        :param raw_str: сырая строка текста.
        :return: форматированный текст.
        """
        # Промежуточная строка, в ней в любом случае меньше 80 символов.
        mid_str = ""
        # Буферная строка, нужна для конкатенации и последующей проверки на кол-во символов.
        buff_str = ""
        # Отформатированная строка.
        format_str = ""
        split_str = raw_str.split(" ")
        # Пробегаемся по списку слов, разделенных пробелом.
        for line in split_str:
            # Восстанавливаем пробел.
            buff_str += "{} ".format(line)
            # Символов меньше 80 и это не конец строки?
            if len(buff_str) <= 80 and not buff_str.endswith("\n "):
                mid_str += "{} ".format(line)
            # Символов меньше 80, но это конец строки?
            elif len(buff_str) <= 80 and buff_str.endswith("\n "):
                if buff_str.endswith("\n "):
                    format_str += buff_str[:-1]
                    buff_str = ""
                    mid_str = ""
            # Символов больше 80 и это конец строки? Были проблемы с обработкой таких строк.
            elif len(buff_str) > 80 and buff_str.endswith("\n "):
                mid_str += "\n"
                format_str += mid_str
                format_str += line
                buff_str = ""
                mid_str = ""
            else:
                mid_str += "\n"
                format_str += mid_str
                buff_str = "{} ".format(line)
                mid_str = "{} ".format(line)

        return format_str

    def _save_file(self, text):
        """
        Функция для сохранения в файл.
        :param text: отформатированный текст.
        :return: None
        """
        file_pwd = urlparse(self.url)
        file_pwd = file_pwd.path.split("/")[1:]
        pwd_to_dir = os.path.join(os.getcwd(), *file_pwd)
        dir_name = os.path.dirname(pwd_to_dir)
        base_name = os.path.basename(pwd_to_dir)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        if not base_name:
            file_name = DEFAULT_FILE_NAME
        else:
            file_name = os.path.splitext(base_name)[0]
        file_name = "{}.txt".format(file_name)
        full_pwd = dir_name + os.sep + file_name
        f = open(full_pwd, "w+")
        f.write(text)
        f.close()
        return None

    def main(self):
        """
        Основная функция.
        :return: None
        """
        result = None
        page = self._get_page(self.url)
        values = self._parse_xpath(page, self.xpath)
        raw_str = self._parse_str(values)
        format_str = self._format_str(raw_str)
        self._save_file(format_str)
        return None

