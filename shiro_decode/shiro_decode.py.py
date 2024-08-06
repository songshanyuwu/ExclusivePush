import re
import base64
from Crypto.Cipher import AES

# Author:zev3n 2021.01.16


def b64_padding(data):
    missing_padding = 4 - len(data) % 4
    if missing_padding:
        data += '=' * missing_padding
    return data


def bytesToHexString(bs):
    return ''.join(['%02X' % b for b in bs])


def extract_data(data):
    reg_exp = r"(?:(?:rememberMe=)|(?:^))\b([A-Za-z0-9+\/=]*)(?:;|$|\s)"
    reg_pattern = re.compile(reg_exp)
    try:
        original_value = reg_pattern.search(data).group(1)
        print(data)
        if len(original_value) < 100:
            print('[-]长度过短，请检查您的输入！')
            exit(0)
        decoded_b64 = base64.b64decode(b64_padding(original_value))
    except AttributeError as err:
        raise AttributeError("[-]未识别格式，请检查您的输入！", err)
    except Exception as wtf:
        print("[-]错误：", wtf)
        raise
    return decoded_b64


def brute_decode(keys, data):
    iv = decoded_b64[0:AES.block_size]
    is_find = False
    for b64_key in keys:
        b64_key = b64_key.strip()
        try:
            cipher = AES.new(base64.b64decode(b64_key), AES.MODE_CBC, iv)
        except ValueError:
            continue
        try:
            result = cipher.decrypt(decoded_b64[AES.block_size:])
        except ValueError:
            raise ValueError("输入数据有误")
        if(result.startswith(b'\xac\xed\x00\x05')):
            # print(result)
            is_find = True
            break
    if is_find:
        return b64_key, iv, result
    else:
        print("解密失败")
        exit(0)


def display(choice, key, iv, data):
    print(f"key(base64编码后)：{key}; IV(HexString)：{bytesToHexString(iv)}")
    print("=" * 40)
    if choice == '1' or choice == '':
        print(data)
    elif choice == '2':
        print(re.sub(r'[\x00-\x1f\x7f-\xff\ufffd]',
                     '.', data.decode('ascii', 'replace')))
    elif choice == '3':
        print(bytesToHexString(data))
    elif choice == '4':
        print(base64.b64encode(data).decode())
    else:
        raise ValueError("请输入正确的选项（数字）")


def read_keys(keys_file):
    with open(keys_file, 'r') as rf:
        keys = rf.readlines()
    return keys


if __name__ == '__main__':
    keys_file = '/Users/songzi/tools/shiro_decode/shiro_keys.txt'
    keys = read_keys(keys_file)
    # print(keys)
    # input_data = """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"""
    input_data = """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"""
    # input_data = input("请输入Shiro Cookie数据,支持自动提取:\n>")

    decoded_b64 = extract_data(input_data)
    real_key, real_iv, result = brute_decode(
        keys, decoded_b64)  # <bytes> result
    choice = input(
        "请选择输出方式:\n1.默认,将不可见字符转义\n2.将不可见字符替换为[.]\n3.HexString\n4.Base64\n>")
    display(choice, real_key, real_iv, result)
