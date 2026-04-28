import requests
from lxml import etree
url = "https://www.biquuge.com/0/112/138573.html"

response = requests.get(url)

root = etree.HTML(response.text)
article_lines = root.xpath("//article[@class='font_max']/text()")
article_lines = article_lines[2:-2]
print (len(article_lines))
print (article_lines[0][5])

first = True

article = ''

for line in article_lines:
        if first:
            first = False
            continue
        else:
            print(line)
            article  += line
        

with open ("1zhang.txt","w",encoding="utf-8") as f:
        f.write(article)
        f.close()        



    
