# -*- coding: utf-8 -*-

from readability import mini_readability
import argparse

def agrp_parse():
    parser = argparse.ArgumentParser(description='Загрузка и синтаксический анализ информации')
    parser.add_argument('-u', '--url', help='URL с которого будет производится загрузка информации')
    parser.add_argument('-c', '--conf', help='Файл конфигураций xpath-запросов для страниц')
    return parser.parse_args()

def main():
    url = agrp_parse()
    mini_readability(url.url, url.conf).main()

if __name__ == '__main__':
    main()