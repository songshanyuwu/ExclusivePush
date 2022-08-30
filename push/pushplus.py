# encoding:utf-8
import requests
import json
token = '49bff5f3bc2f4d1f8415d138ce3e5b51' #在pushpush网站中可以找到
title= '祝开心快乐成长' #改成你要的标题内容
content ='O(∩_∩)O哈哈~' #改成你要的正文内容
url = 'http://pushplus.hxtrip.com/send'
data = {
    "token":token,
    "title":title,
    "content":content
}
body=json.dumps(data).encode(encoding='utf-8')
headers = {'Content-Type':'application/json'}
requests.post(url,data=body,headers=headers)

print(SCKEY)
