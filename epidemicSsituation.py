#!/usr/bin/python3
#coding=utf-8

import requests,random,json
import os

url = "https://c.m.163.com/ug/api/wuhan/app/data/list-total"

pushplus_key = os.environ.get('PUSHPLUSSCKEY') ##PUSHPLUS推送KEY


def HtmlPuch_PushPlus(pneumoniaData): #PushPlus推送
    token = pushplus_key #在pushplus网站中可以找到
    title= '全国疫情数据实时统计' #改成你要的标题内容
    content = pneumoniaData #改成你要的正文内容
    url = f'http://www.pushplus.plus/send?token={token}&title={title}&content={content}&template=html'
    requests.get(url)
    print(requests.get(url))


#随机获取请求头
def UserAgent():
    user_agent_list = ['Mozilla/5.0 (Windows NT 6.2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1464.0 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.16 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.3319.102 Safari/537.36',
                   'Mozilla/5.0 (X11; CrOS i686 3912.101.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 6.2; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.93 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36',
                   'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/20100101 Firefox/17.0.6',
                   'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1468.0 Safari/537.36',
                   'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2224.3 Safari/537.36',
                   'Mozilla/5.0 (X11; CrOS i686 3912.101.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.116 Safari/537.36']
    return {'User-Agent': random.choice(user_agent_list)}


def Get_Url():  # sourcery skip: low-code-quality
    url_json = requests.get(url=url,headers=UserAgent()).json()
    # print(data)

    # 遍历列表字典，重新获取地区或者省市数据
    data2 = ''
    for line in url_json['data']['areaTree']:
        if line['name'] == '中国':
            data ='[+] 标题：' + '全国疫情数据实时统计' + '\n\n' + \
                '统计截至时间：'+ str(line['lastUpdateTime']) +'\n' + \
                '累计确诊：' + str(line['total']['confirm']) + ' ; ' + '较昨日：' + str(line['today']['confirm']) +'\n' + \
                '现有确诊：' + str((line['total']['confirm']-line['total']['dead']-line['total']['heal'])) + ' ; ' + '较昨日：' + str(line['today']['storeConfirm']) +'\n' + \
                '累计死亡：' + str(line['total']['dead']) + ' ; ' + '较昨日：' + str(line['today']['dead']) +'\n' + \
                '累计治愈：' + str(line['total']['heal']) + ' ; ' + '较昨日：' + str(line['today']['heal']) +'\n' + \
                '境外输入：' + str(line['total']['input']) + ' ; ' + '较昨日：' + str(line['today']['input']) +'\n' + \
                '无症状感染者：' + str(line['extData']['noSymptom']) + ' ; ' + '较昨日：' + str(line['extData']['incrNoSymptom']) +'\n'
            for l2 in line['children'] :
                if (l2['total']['confirm']-l2['total']['heal']-l2['total']['dead']) != 0:
                    data2 = data2 + '\n✁-----------------------------------\n' + \
                         '省/市-现明确-总确诊-较昨日+ 死亡-治愈\n' + \
                        l2['name'] + ':' + l2['name'] + '  ' + str(l2['today']['confirm']) + \
                         '  ' + str(l2['total']['confirm']) + '  ' + str(l2['today']['confirm']) + \
                         '  ' + str(l2['total']['dead']) + '  ' + str(l2['total']['heal'])
                for l3 in l2['children']:
                    if (l3['total']['confirm']-l3['total']['heal']-l3['total']['dead']) != 0:
                        if l3['today']['confirm'] != 0:
                            if l3['name'] == '未明确地区':
                                l3['name']='未明地'
                            data2 = data2 + '\n' + \
                                l2['name'] + '-' + l3['name'] + '  ' + str(l3['today']['confirm']) + \
                                '  ' + str(l3['total']['confirm']) + '  ' + str(l3['today']['confirm']) + \
                                '  ' + str(l3['total']['dead']) + '  ' + str(l3['total']['heal'])


    pneumoniaData = data + data2
    print(pneumoniaData)
    print(len(pneumoniaData))
    HtmlPuch_PushPlus(pneumoniaData)
    print('ok')


if __name__ == '__main__':
    Get_Url()
