# -*- coding: utf-8 -*-
import re
import requests
from lxml import etree
import time
import json
import os


###############################################
# 云函数内置的库中 没有需要的 lxml库 需要自行安装
# A. 终端-新终端
# B. 代码下面会有个框-(终端)-输入命令(切换到文件的目录)
#     cd src
#     pip3 install  lxml yagmail -t .
###############################################

PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY') ##PUSHPLUS推送KEY

# 设置请求头
headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36 Edg/96.0.1054.57",
        "Referer": "https://tv.cctv.com/lm/xwlb/",
        "Accept": "text/html, */*; q=0.01"
    }

# 获取日期
timeStruct = time.localtime()
strTime = time.strftime("%Y%m%d", timeStruct)
# print(strTime)
# 如果是上午8点以后推送的，括号外的“-1”要删除
str_time = int(strTime)-1   
# str_time = int(strTime)


# # 获取新闻
# def hq_news():
#     news = []
#     url = f'https://tv.cctv.com/lm/xwlb/day/{str_time}.shtml'
#     response = requests.get(url, headers=headers)
#     response.encoding = 'RGB'
#     resp = response.text
#     etr = etree.HTML(resp)
#     # titles = etr.xpath("//div[@class='title']/text()")  #已经过期，网站页面调整，本次更新2022-01-23
#     titles = etr.xpath("//li/a/@title")
#     hrefs = etr.xpath("//li/a/@href")
#     i = 0 
#     for title, href in zip(titles, hrefs):
#         news_response = requests.get(href, headers=headers)
#         news_response.encoding = 'RGB'
#         news_resp = news_response.text
#         # news_th = etree.HTML(news_resp).xpath('string(//*[@id="about_txt"]/div[2]/div)')
#         # news_th_tmp = etree.HTML(news_resp).xpath('//*[@id="about_txt"]/div[2]/div//text()')
#         news_th_tmp = etree.HTML(news_resp).xpath('//*[@id="content_area"]/p[*]/text()')
#         news_th = ""
#         for i,n in enumerate(news_th_tmp):
#             if i < 1:
#                 news_th = news_th + n
#             else:
#                 news_th = news_th + "<br>" + n
#         # news.append(f"##{title}\n{news_th}\n##视频地址：{href}\n\n")
#         # news.append(f"##{title}<br>{news_th}<br>##视频地址：{href}<br><br>")
#         news.append(f"<b>{title}</b><br>{news_th}<br><b>视频地址</b> <a href='{href}'>{href}</a><br><br>")
#     return news

# 获取新闻-20250120
def hq_news():
    news = []
    url = f'https://tv.cctv.com/lm/xwlb/day/{str_time}.shtml'
    response = requests.get(url, headers=headers)
    response.encoding = 'RGB'
    resp = response.text
    etr = etree.HTML(resp)
    # titles = etr.xpath("//div[@class='title']/text()")  #已经过期，网站页面调整，本次更新2022-01-23
    titles = etr.xpath("//li/a/@title")
    hrefs = etr.xpath("//li/a/@href")

    i = 0 
    for title, href in zip(titles, hrefs):
        news_response = requests.get(href, headers=headers)
        news_response.encoding = 'RGB'
        news_resp = news_response.text
        etr_news = etree.HTML(news_resp)
        
        # 提取包含 strong 和 p 元素的 div 元素
        div_elements = etr_news.xpath('//div[@id="content_area"]/p')
        result = ""
        for div_element in div_elements:
            strong_elements = div_element.xpath('strong/text()')
            p_elements = div_element.xpath('text()')
            # 处理 strong 元素
            if strong_elements and strong_elements[0]!= "央视网消息":
                result += f"<b>{strong_elements[0]}</b><br>"
            # 处理 p 元素
            if p_elements and p_elements[0]!= "（新闻联播）：":
                # result += f"{p_elements[0]}<br>"
                # 在 p 元素开头添加两个空格
                p_text = "&nbsp;&nbsp;" + p_elements[0].strip()  
                result += f"{p_text}<br>"
        # news.append(f"<b>{title}</b><br>{result}<br><b>视频地址</b> <a href='{href}'>{href}</a><br>")
        news.append(f"<b>{title}</b><br>{result}<br><br>")
    return news

# PushPlus推送
def PushPlus(newstitle, newscontext):
    PushPlus = 'http://www.pushplus.plus/send'
    data = {
        "token":PUSHPLUSSCKEY,
        "title":newstitle,
        "content":newscontext,
        "template":"html"
    }
    body=json.dumps(data).encode(encoding='utf-8')
    requests.post(url=PushPlus,data=body,headers=headers)
    return 'PushPlus推送成功'


# 在腾讯云SCF用这个，这个函数名和执行方法有关系
# (event, context)就这样写，也没有搞明白为什么这样写，可能云函数就是这样定义程序执行入口的
# 难受的是这个一直没有从帮助文档上找到，可能人家以为这个忒简单了，┭┮﹏┭┮
# def main_handler(event, context):

# 在服务器上用这个
if __name__ == '__main__':
    newstitle = str(str_time) + "新闻联播文字稿"
    news = hq_news()
    # print(news)
    # newscontext = "".join(news)
    # 推送限制字符应该在10000一下，多了就丢弃不响应了；所以这里需要拆分一下，分成多个推送消息
    # 这里也是个坑，推送上没有说明，但是测试结果可以证实这一点
    newscontext = ""
    newscontext_tmp = ""
    for i in news:
        if len(newscontext) < 8888:
            newscontext_tmp = newscontext + i
            if len(newscontext_tmp) >= 8888:
                #p rint(newscontext)
                print("发送一次推送")
                PushPlus(newstitle, newscontext)
                newscontext = ""
                newscontext_tmp = ""
            else:
                newscontext = newscontext_tmp
    if len(newscontext) != 0:
        # print(newscontext)
        print("发送最后一次推送")
        PushPlus(newstitle, newscontext)
        
