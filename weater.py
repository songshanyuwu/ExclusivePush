#!/usr/bin/python3
#coding=utf-8

import requests, json
import os


PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY') ##PUSHPLUS推送KEY
SERVERSCKEY = os.environ.get('SERVERSCKEY')     ##Server酱推送KEY
COOLSCKEY = os.environ.get('COOLSCKEY')         ##CoolPush酷推KEY


def get_iciba_everyday():
    icbapi = 'http://open.iciba.com/dsapi/'
    eed = requests.get(icbapi)
    bee = eed.json()  #返回的数据
    english = bee['content']
    zh_CN = bee['note']
    str = english + '\n' + zh_CN
    return str


def PushPlus(info): #PUSHPLUS酱推送
    token = PUSHPLUSSCKEY               #在pushpush网站中可以找到
    title= u"天气推送"                   #改成你要的标题内容
    content = info.replace('\n','\n\n') #改成你要的正文内容
    url = 'http://pushplus.hxtrip.com/send'
    data = {
        "token":token,
        "title":title,
        "content":content,
        "template":"json"
    }
    body=json.dumps(data).encode(encoding='utf-8')
    headers = {'Content-Type':'application/json'}
    requests.post(url, data=body, headers=headers)


def ServerPush(info): #Server酱推送
    api = "https://sc.ftqq.com/{}.send".format(SERVERSCKEY)
    title = u"天气推送"
    content = info.replace('\n','\n\n')
    data = {
        "text": title,
        "desp": content
    }
    # print(content)
    requests.post(api, data=data)
    
    
def CoolPush(info): #CoolPush酷推
    # cpurl = 'https://push.xuthus.cc/group/'+COOLSCKEY   #推送到QQ群
    # cpurl = 'https://push.xuthus.cc/send/' + COOLSCKEY  # 推送到个人QQ
    api='https://push.xuthus.cc/send/{}'.format(COOLSCKEY)
    # print(api)
    # print(info)
    requests.post(api, info.encode('utf-8'))
    
    
def main():
    try:
        api = 'http://t.weather.itboy.net/api/weather/city/'             #API地址，必须配合城市代码使用
        city_code = '101120101'   #进入https://where.heweather.com/index.html查询你的城市代码
        tqurl = api + city_code
        response = requests.get(tqurl)
        d = response.json()         #将数据以json形式返回，这个d就是返回的json数据
        weather = {}
        if(d['status'] == 200):     #当返回状态码为200，输出天气状况
            # 天气提示内容
            weather['天气更新时间'] = d["time"]
            weather['省市'] = d["cityInfo"]["parent"] + ' ' + d["cityInfo"]["city"]
            weather['日期'] = d["data"]["forecast"][0]["ymd"] + ' ' + d["data"]["forecast"][0]["week"]
            weather['天气'] = d["data"]["forecast"][0]["type"]
            weather['温度'] = d["data"]["forecast"][0]["high"] + ' / ' + d["data"]["forecast"][0]["low"]
            weather['天气质量'] = d["data"]["quality"] + ' /PM2.5:' + str(d["data"]["pm25"]) + ' /PM10:' + str(d["data"]["pm10"])
            weather['风力风向'] = d["data"]["forecast"][0]["fx"] + ' ' +  d["data"]["forecast"][0]["fl"]
            weather['感冒指数'] = d["data"]["ganmao"]
            weather['温馨提示'] = d["data"]["forecast"][0]["notice"]
            weather['每日英语句子'] = get_iciba_everyday()

            # requests.post(cpurl,tdwt.encode('utf-8')) #把天气数据转换成UTF-8格式，不然要报错。
            
            PushPlus(str(weather))
            
            # 天气提示内容
            tdwt = "【今日份天气】\n城市： " + d["cityInfo"]["parent"] + d["cityInfo"]["city"] + \
                   "\n日期： " + d["data"]["forecast"][0]["ymd"] + "\n星期: " + d["data"]["forecast"][0]["week"] + \
                   "\n天气: " + d["data"]["forecast"][0]["type"] + "\n温度: " + d["data"]["forecast"][0]["high"] + " / "+ d["data"]["forecast"][0]["low"] + \
                   "\n湿度: " + d["data"]["shidu"] + "\nPM25: " + str(d["data"]["pm25"]) + "\nPM10: " + str(d["data"]["pm10"]) + \
                   "\n空气质量: " + d["data"]["quality"] + "\n风力风向: " + d["data"]["forecast"][0]["fx"] + d["data"]["forecast"][0]["fl"] + \
                   "\n感冒指数: "  + d["data"]["ganmao"] + "\n温馨提示： " + d["data"]["forecast"][0]["notice"] + "\n更新时间: " + d["time"] + \
                   "\n✁-----------------------------------------\n" + get_iciba_everyday()
            # print(tdwt)
            ServerPush(tdwt)
            CoolPush(tdwt)
    except Exception:
        error = '【出现错误】\n　　今日天气推送错误，请检查服务或网络状态！'
        print(error)
        print(Exception)

if __name__ == '__main__':
    main()
