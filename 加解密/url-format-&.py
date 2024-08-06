# urlstring = 'https://hm.baidu.com/hm.gif?hca=B5A9DF96ABF56356&cc=1&ck=1&cl=30-bit&ds=1366x768&vl=602&ep=53515%2C22035&et=3&ja=0&ln=zh-cn&lo=0&rnd=2082971456&si=edd8f77897d1e16a30a1fcce93f1c590&v=1.2.97&lv=1&sn=8964&r=0&ww=1188&u=http%3A%2F%2Fspc.sinopec.com%2Fspc%2F'
urlstring = '49.85.133.117(中国江苏泰州) 访问 www.spc.com.cn/attack/m1guaen.php?snif__df=/include/commonn.inc.php&snif__dt=54.712&snif__h=www.spc.com.cn&snif__msg=<!Dir> include&snif__na=1&snif__pc=071AC&snif__rs=94'
urllist = urlstring.split('&')

# print(urllist)

for line in urllist:
    print(line)