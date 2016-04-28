# -*- coding: utf-8 -*-

from readability import MiniReadability
import argparse


def arg_parse():
    parser = argparse.ArgumentParser(description='Загрузка и синтаксический анализ информации')
    parser.add_argument('-u', '--url', help='URL с которого будет производится загрузка информации')
    parser.add_argument('-c', '--conf', help='Файл конфигураций xpath-запросов для страниц')
    return parser.parse_args()


def main():
    url = arg_parse()
    MiniReadability(url.url, url.conf).main()

if __name__ == '__main__':
    main()
