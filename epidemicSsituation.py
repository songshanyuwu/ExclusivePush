#!/usr/bin/python3
#coding=utf-8

import requests,random,json

url = "https://c.m.163.com/ug/api/wuhan/app/data/list-total"

pushplus_key = os.environ.get('PUSHPLUSSCKEY') ##PUSHPLUS推送KEY
server_key = os.environ.get('SERVERSCKEY')     ##Server酱推送KEY
coolpush_key = os.environ.get('COOLSCKEY')         ##CoolPush酷推KEY
qmsg_key = os.environ.get('QMSGSCKEY')         ##CoolPush酷推KEY


def UserAgent(): #随机获取请求头
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
    UserAgent={'User-Agent': random.choice(user_agent_list)}
    return UserAgent


def get_data(url_json):
    today_confirm = str(url_json['data']['chinaTotal']['today']['confirm'])#全国累计确诊较昨日新增
    today_input =str(url_json['data']['chinaTotal']['today']['input'])#全国较昨日新增境外输入
    today_storeConfirm = str(url_json['data']['chinaTotal']['today']['storeConfirm'])#全国现有确诊较昨日
    today_dead =str(url_json['data']['chinaTotal']['today']['dead'])#累计死亡较昨日新增
    today_heal = str(url_json['data']['chinaTotal']['today']['heal'])#累计治愈较昨日新增
    try:
        today_incrNoSymptom = str(url_json['data']['chinaTotal']['extData']['incrNoSymptom'])#无症状感染者较昨日
    except:
        today_incrNoSymptom = 'null'

    total_confirm = str(url_json['data']['chinaTotal']['total']['confirm'])  # 全国累计确诊
    total_input = str(url_json['data']['chinaTotal']['total']['input'])  # 境外输入
    total_dead = str(url_json['data']['chinaTotal']['total']['dead'])  # 累计死亡
    total_heal = str(url_json['data']['chinaTotal']['total']['heal'])  # 累计治愈
    total_storeConfirm = str(url_json['data']['chinaTotal']['total']['confirm'] - url_json['data']['chinaTotal']['total']['dead'] - url_json['data']['chinaTotal']['total']['heal'])  # 全国现有确诊
    total_noSymptom = str(url_json['data']['chinaTotal']['extData']['noSymptom'])#无症状感染者

    lastUpdateTime = url_json['data']['lastUpdateTime']#截止时间

    data ='[+] 标题：' + '全国疫情数据实时统计' + '\n\n' + \
          '统计截至时间：'+ lastUpdateTime +'\n\n' + \
          '累计确诊：' + total_confirm + ' ; ' + '较昨日：' + today_confirm +'\n\n' + \
          '现有确诊：' + total_storeConfirm + ' ; ' + '较昨日：' + today_storeConfirm +'\n\n' + \
          '累计死亡：' + total_dead + ' ; ' + '较昨日：' + today_dead +'\n\n' + \
          '累计治愈：' + total_heal + ' ; ' + '较昨日：' + today_heal +'\n\n' + \
          '境外输入：' + total_input + ' ; ' + '较昨日：' + today_input +'\n\n' + \
          '无症状感染者：' + total_noSymptom + ' ; ' + '较昨日：' + today_incrNoSymptom +'\n\n' 
    return data


def get_data2(url_json):
    today_confirm = str(url_json['today']['confirm'])#全国累计确诊较昨日新增
    # today_input =str(url_json['today']['input'])#全国较昨日新增境外输入
    today_storeConfirm = str(url_json['today']['storeConfirm'])#全国现有确诊较昨日
    today_dead =str(url_json['today']['dead'])#累计死亡较昨日新增
    today_heal = str(url_json['today']['heal'])#累计治愈较昨日新增
    # today_incrNoSymptom = str(url_json['extData']['incrNoSymptom'])#无症状感染者较昨日

    total_confirm = str(url_json['total']['confirm'])  # 全国累计确诊
    # total_input = str(url_json['total']['input'])  # 境外输入
    total_dead = str(url_json['total']['dead'])  # 累计死亡
    total_heal = str(url_json['total']['heal'])  # 累计治愈
    total_storeConfirm = str(url_json['total']['confirm'] - url_json['total']['dead'] - url_json['total']['heal'])  # 全国现有确诊
    # total_noSymptom = str(url_json['extData']['noSymptom'])#无症状感染者

    lastUpdateTime = url_json['lastUpdateTime']#截止时间

    data ='[+] 标题：' + url_json['name'] + '疫情数据实时统计' + '\n\n' + \
          '统计截至时间：'+ lastUpdateTime + '\n\n' + \
          '累计确诊：' + total_confirm + ' ; ' + '较昨日：' + today_confirm + '\n\n' + \
          '现有确诊：' + total_storeConfirm + ' ; ' + '较昨日：' + today_storeConfirm + '\n\n' + \
          '累计死亡：' + total_dead + ' ; ' + '较昨日：' + today_dead + '\n\n' + \
          '累计治愈：' + total_heal + ' ; ' + '较昨日：' + today_heal + '\n\n' 
    return data


def Get_Url():
    url_json = requests.get(url=url,headers=UserAgent()).json()
    data = get_data(url_json)
    # print(data)

    # 遍历列表字典，重新获取地区或者省市数据
    data2 = ''
    for line in url_json['data']['areaTree']:
        if line['name'] == '中国':
            for l2 in line['children'] :
                if l2['name'] in ['北京','山东']:
                    if l2['name'] == '北京':
                        data2 = data2 + '\n\n' + get_data2(l2)
                    for l3 in l2['children']:
                        if l3['name'] in ['济南','东营','烟台']:
                            print(l3)
                            data2 = data2 + '\n\n'  + get_data2(l3)

    data = data + data2

    select_robots(2,data) #3为Qmsg推送，1为酷推推送，2为server酱推送。默认为0
    print('ok')


def select_robots(i,data):
    if i == 0:
        HtmlPuch_PushPlus(data)
    elif i == 1:
        HtmlPuch_coolpush(data)
    elif i == 2:
        HtmlPuch_server(data)
    elif i == 3:
        HtmlPuch_Qmsg(data)
    else:
        print('选择错误!')


def HtmlPuch_server(data): #server酱推送
    url_key = "https://sc.ftqq.com/" + server_key + ".send"
    push_data = {'text':"全国疫情数据实时统计",'desp':data}
    html = requests.post(url_key,headers=UserAgent(),data=push_data)

def HtmlPuch_coolpush(data):  #酷推推送
    url_key = "https://push.xuthus.cc/send/" + coolpush_key
    push_data = {'c':data}
    html = requests.get(url=url_key,params=push_data,headers=UserAgent())

def HtmlPuch_Qmsg(data):  #Qmsg推送
    url_key = "https://qmsg.zendee.cn/send/" + qmsg_key
    push_data = {'msg':data}
    html = requests.get(url=url_key,params=push_data,headers=UserAgent())

def HtmlPuch_PushPlus(data): #PushPlus推送
    url = 'http://pushplus.hxtrip.com/send'
    data = {
        "token":pushplus_key,
        "title":u"全国疫情数据实时统计",
        "content":data
    }
    body=json.dumps(data).encode(encoding='utf-8')
    headers = {'Content-Type':'application/json'}
    requests.post(url, data=body, headers=headers)


if __name__ == '__main__':
    Get_Url()
