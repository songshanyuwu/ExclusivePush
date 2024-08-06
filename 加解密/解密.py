import zipfile
import os
import time
import sys
import random


'''
源代码描述：
1：代码中，变量统一使用zip代表压缩包


2：关于空密码
测试发现，当一个压缩包是无密码的时候，给extractall的pwd参数指定密码，依然可以正确提取压缩包
因此无需写代码检查压缩包时候有密码
否则，检查有无密码报异常，有密码爆破再爆异常，搞得代码会很复杂


3：关于zfile.extractall
破解密码用到的zfile.extractall中
extractall要求输入的是字节类型，所以需要手动转


4：关于异常，前面的那段注释
使用try/except时候，pycharm报告Exception太宽泛，我们应该指定异常类型
如果不确定有可能发生的错误类型
在 try 语句前加入 # noinspection PyBroadException 即可让pycharm闭嘴
但是except Exception as e中的e仍然会被pycharm报告说，这个变量没有使用


5：关于解压乱码
我这里是通过修改zipfile的源代码来解决的
修改源代码时，如果无法找到【if zinfo.flag_bits & 0x800】
可能是zipfile版本的问题，请试着搜索【if fheader[_FH_GENERAL_PURPOSE_FLAG_BITS] & 0x800】，或者【fname_str = fname.decode("utf-8")】
定位的方式是多样的，不必拘泥
详情参见：
https://secsilm.blog.csdn.net/article/details/79829247
https://wshuo.blog.csdn.net/article/details/80146766?spm=1001.2014.3001.5506


6：关于代码运行位置
由于我的代码往往跟操作的文件不在一个地方，所以在run()函数中使用
#os.chdir(r'')  # 此路径是测试的时候使用，用来手动设定压缩包路径
来手动设定脚本工作目录
'''




# 主备前提工作：检查出当前路径中的压缩包，并创建一个同名的文件夹
def ready_work():
    files = os.listdir()  # 获取脚本工作路径中的所有文件


    for file in files:  # 遍历脚本工作路径中的所有文件
        if file.endswith('.zip'):  # 找出脚本工作路径中的所有zip文件
            # 开始制造一个新文件夹的路径，用来存放解压结果
            a = os.path.splitext(file)  # 分离压缩包的名字和后缀
            new_path = os.path.join(os.path.abspath('.'), str(a[0]))  # 把当前脚本运行的路径和压缩包的文件名拼接成新的路径
            # 检查新文件夹的路径是否已存在，如果有就直接使用，如果没有就创建它
            if os.path.exists(new_path):
                pass
            else:
                os.makedirs(new_path)
            return new_path, file




# 纯数字爆破
def get_zipfile():
    math_max = 1000000  # 设置数字密码的上限
    math_min = 1  # 设置数字密码是下限
    print('默认输入数字下限是1,如需重设请输入,否则请回车键跳过')
    math_min_input = input('')
    print('默认数字上限是1000000(1百万),如需重设请输入,否则请回车键跳过')
    math_max_input = input('')


    if len(math_max_input):
        math_max = int(math_max_input)
    else:
        pass
    if len(math_min_input):
        math_min = int(math_min_input)
    else:
        pass


    new_path, file = ready_work()  # 用来接收ready_work()返回的两个变量
    print('爆破开始')
    count = 0


    # 开始解压文件
    with zipfile.ZipFile(file) as zip_file:  # 读取压缩文件
        for num in range(math_min, math_max):  # 设置数字密码区间
            start_time = time.time()
            # noinspection PyBroadException
            try:
                pwd = str(num)
                zip_file.extractall(path=new_path, pwd=pwd.encode('utf-8'))
                print('[+]' + str(file) + ' 解压密码是：', pwd)
                end_time = time.time()
                print('[-] 耗时：{}秒'.format(str(end_time - start_time)))
                count = count + 1  # count最后加1一次，用来算成成功的这次
                print('[-] 累计尝试{}'.format(count))
                sys.exit(0)  # 让程序在得到结果后，就停止运行，正常退出
            except Exception as e:
                count += 1  # 统计总共失败了多少次
                pass




# 实现数字字母组合爆破
class MyIter(object):
    word = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 原始的密码本


    def __init__(self, min_len, max_len):  # 迭代器实现初始方法，传入参数
        # 下面的if-else是为了解决extract函数中，for循环中传递的密码长度可能前者的值大于后者，这一bug
        if min_len < max_len:
            self.min_len = min_len
            self.max_len = max_len
        else:
            self.min_len = max_len
            self.max_len = min_len


    def __iter__(self):  # 直接返回self实列对象
        return self


    def __next__(self):  # 通过不断地轮循，生成密码
        result_word = ''
        for i in range(0, random.randint(self.min_len, self.max_len)):  # randint取值为[]左右闭区间
            result_word += random.choice(MyIter.word)  # 从word中随机取选取一个值，并把选取几次的结果拼接成一个字符，即一个密码
        return result_word




def extract():
    password_min = input('请输入密码长度下限：')  # 设置密码区间长度
    if password_min.isdecimal():
        # 上面input输入数字，虽说input接收过来的数字是字符型，但是isdecimal认为它是一个数字，这是isdecimal内部的问题
        # 但是password_min的值仍然是字符型，还是需要isdecimal判断后，再手动转换为int型
        password_min = int(password_min)
    else:
        print('请输入数字！')
    password_max = input('请输入密码长度上限：')  # 设置密码区间长度
    if password_max.isdecimal():
        password_max = int(password_max)
    else:
        print('请输入数字！')


    new_path, file = ready_work()  # 用来接收ready_work()返回的两个变量
    print('爆破开始')
    count = 0
    with zipfile.ZipFile(file) as zip_file:  # 读取压缩文件
        for password in MyIter(password_min, password_max):  # 随机迭代出指定长度区间内的密码，在不明确位数的时候做相应的调整
            start_time = time.time()
            # noinspection PyBroadException
            try:
                zip_file.extractall(path=new_path, pwd=str(password).encode('utf-8'))
                print('[+]' + str(file) + ' 解压密码是：' + password)
                end_time = time.time()
                print('[-] 耗时：{}秒'.format(str(end_time - start_time)))
                count = count + 1  # count最后加1一次，用来算成成功的这次
                print('[-] 累计尝试{}'.format(count))
                sys.exit(0)
            except Exception as e:
                count += 1
                pass




# 实现密码本爆破
def password_file_baopo():
    new_path, file = ready_work()  # 用来接收ready_work()返回的两个变量
    with zipfile.ZipFile(file) as zip_file:


        # 设置密码本
        # 用来判断用户是否正正确输入数字1或者0
        print('使用当前工作路径中的txt文件作为密码本请输入：1')
        print('手动指定密码本路径请输入：0')
        while True:
            user_choice_mode = input()
            if user_choice_mode == str(1) or user_choice_mode == str(0):
                break
            else:
                print("请正确输入数字 1 或者 0！")
                continue
        user_choice_mode = int(user_choice_mode)
        if user_choice_mode:  # 如果用户选择了模式1
            all_files = os.listdir()
            for all_file in all_files:
                if all_file.endswith('.txt'):
                    password_file = str(all_file)
        else:
            password_file = input(r'请输入密码本的路径：')


        print('爆破开始')
        count = 0
        start_time = time.time()
        try:
            with open(password_file, 'r', encoding='utf8') as pwdfile:  # 逐行读取密码本
                word = pwdfile.readlines()
                for w in word:
                    w = w.replace('\n', '')


                    # 尝试破解zip文件
                    # noinspection PyBroadException
                    try:
                        zip_file.extractall(path=new_path, pwd=str(w).encode('utf-8'))
                        print('[+]' + str(file) + ' 解压密码是：', str(w))
                        end_time = time.time()
                        print('[-] 耗时：{}秒'.format(str(end_time - start_time)))
                        count = count + 1  # count最后加1一次，用来算成成功的这次
                        print('[-] 累计尝试{}'.format(count))
                        sys.exit(0)
                    except Exception as e:
                        count += 1
                        pass
        except Exception as f:
            print('你输入的路径有问题！请检查，错误信息是：')
            print(f)




# 运行程序
def run():
    print('一个ZIP爆破工具')
    print('需要把脚本和压缩包放在同一个文件夹中,默认对当前路径下所有的压缩包逐个爆破')
    os.chdir(r'G:\桌面\111')  # 测试的时候使用，手动修改脚本工作路径
    print('[+]输入1:程序自动进行纯数字爆破')
    print('[+]输入2:程序自动进行字母数字组合爆破，效率低下不推荐')
    print('[+]输入3:使用密码本进行爆破')
    print()
    user_choice = int(input('[-]输入:'))
    if user_choice == 1:
        print('纯数字爆破模式--->')
        get_zipfile()
    elif user_choice == 2:
        print('数字字母爆破模式--->')
        extract()
    else:
        print('密码本爆破模式--->')
        password_file_baopo()




if __name__ == '__main__':
    run()
