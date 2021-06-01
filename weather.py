#!/usr/bin/python3
#coding=utf-8

import requests, json
import os


# PUSHPLUSSCKEY = os.environ.get('PUSHPLUSSCKEY') ##PUSHPLUS推送KEY
# SERVERSCKEY = os.environ.get('SERVERSCKEY')     ##Server酱推送KEY
# COOLSCKEY = os.environ.get('COOLSCKEY')         ##CoolPush酷推KEY


def HtmlPuch_PushPlus(pneumoniaData): #PushPlus推送
    token = pushplus_key #在pushplus网站中可以找到
    title= '全国疫情数据实时统计' #改成你要的标题内容
    content = pneumoniaData #改成你要的正文内容
    url = 'http://www.pushplus.plus/send?token='+token+'&title='+title+'&content='+content+'&template=html'
    requests.get(url)

def PushPlus(info): #PUSHPLUS酱推送
    token = PUSHPLUSSCKEY               #在pushpush网站中可以找到
    title= '天气推送'                   #改成你要的标题内容
    content = info #改成你要的正文内容
    url = 'http://www.pushplus.plus/send?token='+token+'&title='+title+'&content='+content+'&template=html'
    requests.get(url)


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
    
    
def get_iciba_everyday():
    icbapi = 'http://open.iciba.com/dsapi/'
    eed = requests.get(icbapi)
    bee = eed.json()  #返回的数据
    english = bee['content']
    zh_CN = bee['note']
    str = english + '\n' + zh_CN
    return str


def weather1(city_code):
    try:
        api = 'http://t.weather.itboy.net/api/weather/city/'             #API地址，必须配合城市代码使用
        # city_code = '101120101'   #进入https://where.heweather.com/index.html查询你的城市代码
        tqurl = api + city_code
        response = requests.get(tqurl)
        d = response.json()         #将数据以json形式返回，这个d就是返回的json数据
        weather = {}
        if(d['status'] == 200):     #当返回状态码为200，输出天气状况
            # 天气提示内容
            print('获取到天气:' + city_code)
            weather['天气更新时间'] = d["time"]
            weather['省市'] = d["cityInfo"]["parent"] + ' ' + d["cityInfo"]["city"]
            weather['日期'] = d["data"]["forecast"][0]["ymd"] + ' ' + d["data"]["forecast"][0]["week"]
            weather['昨日温度'] = d["data"]["yesterday"]["high"] + ' / ' + d["data"]["yesterday"]["low"] + ' / ' + d["data"]["yesterday"]["type"]
            weather['-今日温度'] = d["data"]["forecast"][0]["high"] + ' / ' + d["data"]["forecast"][0]["low"] + ' / ' + d["data"]["forecast"][0]["type"]
            weather['明日温度'] = d["data"]["forecast"][1]["high"] + ' / ' + d["data"]["forecast"][1]["low"] + ' / ' + d["data"]["forecast"][1]["type"]
            weather['后日温度'] = d["data"]["forecast"][2]["high"] + ' / ' + d["data"]["forecast"][2]["low"] + ' / ' + d["data"]["forecast"][2]["type"]
            weather['天气质量'] = d["data"]["quality"] + ' /PM2.5:' + str(d["data"]["pm25"]) + ' /PM10:' + str(d["data"]["pm10"])
            weather['风力风向'] = d["data"]["forecast"][0]["fx"] + ' ' +  d["data"]["forecast"][0]["fl"]
            weather['感冒指数'] = d["data"]["ganmao"]
            weather['温馨提示'] = d["data"]["forecast"][0]["notice"]
            weather['每日英语句子'] = get_iciba_everyday()
    
    except Exception:
        error = '【出现错误】\n　　今日天气推送错误，请检查服务或网络状态！'
        print(error)
        print(Exception)
        weather = ''
    return weather


def weather2(city_code):
    try:
        api = 'http://t.weather.itboy.net/api/weather/city/'             #API地址，必须配合城市代码使用
        # city_code = '101120101'   #进入https://where.heweather.com/index.html查询你的城市代码
        tqurl = api + city_code
        response = requests.get(tqurl)
        d = response.json()         #将数据以json形式返回，这个d就是返回的json数据
        weather = {}
        if(d['status'] == 200):     #当返回状态码为200，输出天气状况
            # 天气提示内容
            tdwt = "【今日份天气】\n城市： " + d["cityInfo"]["parent"] + d["cityInfo"]["city"] + "  /  " + d["data"]["forecast"][0]["ymd"] + d["data"]["forecast"][0]["week"] + \
                   "\n更新时间: " + d["time"] + \
                   "\n昨日温度: " + d["data"]["yesterday"]["high"] + "  /  " + d["data"]["yesterday"]["low"] + "  /  " + d["data"]["yesterday"]["type"] + \
                   "\n-今日温度: " + d["data"]["forecast"][0]["high"] + "  /  " + d["data"]["forecast"][0]["low"] + "  /  " + d["data"]["forecast"][0]["type"] + \
                   "\n明日温度: " + d["data"]["forecast"][1]["high"] + "  /  " + d["data"]["forecast"][1]["low"] + "  /  " + d["data"]["forecast"][1]["type"] + \
                   "\n后日温度: " + d["data"]["forecast"][2]["high"] + "  /  " + d["data"]["forecast"][2]["low"] + "  /  " + d["data"]["forecast"][2]["type"] + \
                   "\n湿度  /  空气质量  /  PM2.5  /  PM10  /  风力风向\n" +  \
                   d["data"]["shidu"] + "  /  "+ d["data"]["quality"] + "  /  "+ str(d["data"]["pm25"]) + "  /  "+ str(d["data"]["pm10"]) + "  /  "+ d["data"]["forecast"][0]["fx"] + d["data"]["forecast"][0]["fl"] + \
                   "\n感冒指数: "  + d["data"]["ganmao"] + \
                   "\n温馨提示： " + d["data"]["forecast"][0]["notice"] + \
                   "\n✁-----------------------------------------\n"
            # print(tdwt)
    except Exception:
        error = '【出现错误】\n　　今日天气推送错误，请检查服务或网络状态！'
        print(error)
        print(Exception)
        tdwt = ''
    return tdwt


def get_dict(d1, d2):
    return {a: dict(c.items()+d.items()) if all(not isinstance(h, dict) for _, h in c.items()) and all(not isinstance(h, dict) for _, h in d.items()) else get_dict(c, d) for (a, c), (_, d) in zip(d1.items(), d2.items())}

def main():
    # 只查询一个地区的天气，建议使用PushPlus的json  需要传参dist
    # city_codes = '101120101'
    # weatherContent1 = weather1(city_codes)
    # # print(str(weatherContent1))
    # PushPlus(str(weatherContent1))

    city_codes = ['101120101', '101121201', '101010300', '101120504']
    weatherContent2 = ''
    for item in city_codes:
        weatherContent2 =  weatherContent2 + weather2(item)
    # print(weatherContent2)
    # ServerPush(weatherContent2 + get_iciba_everyday())
    PushPlus(weatherContent2 + get_iciba_everyday())


if __name__ == '__main__':
    main()
    
