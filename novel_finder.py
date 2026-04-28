import requests
from lxml import etree
import os

base_number = 138573
number = str(base_number) + "_1"


def get_url(number):
    url = "https://www.biquuge.com/0/112/" + number + ".html"
    return (url)

def get_article_lines(url):
    response = requests.get(url)
    
    root = etree.HTML(response.text)
    article_lines = root.xpath("//article[@class='font_max']/text()")
    
    
    return (article_lines)

def get_article(article_lines):
    article = ''
    article_lines = article_lines[2:-2]

    for line in article_lines:
        article += line
        
    return article

def get_file(number, base_number):
    chapter = int(number[0:6]) - base_number + 1
    return ("第" + str(chapter) + "章.txt")    

def write_in(number, file):
    url = get_url(number)
    article_lines = get_article_lines(url)
    article = get_article(article_lines)
    
    folder = r"C:\Users\ultimate_handsome\Desktop\novel"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, file)
     
    with open (file_path,"a",encoding="utf-8") as f:
            f.write(article)
            f.close()


def next(number):
    url = get_url(number)
    article_lines = get_article_lines(url)
    
    if article_lines[1][6] == article_lines[1][8]:
        number = str(int(number[0:6]) + 1)
    else:
        number = number[0:6] + "_" + str(int(article_lines[1][6]) + 1)
    
    return number

def check_chapter(number):
    new_number = next(number)
    if new_number[0:6] == number[0:6]:
        return False
    else:
        return True


i = 0
while(i < 3):
    file = get_file(number, base_number)
    write_in(number, file)
    if check_chapter(number):
        i += 1
    number = next(number)
'''
url = get_url(number)
article_lines = get_article_lines(url)
print(article_lines[1][6])
'''