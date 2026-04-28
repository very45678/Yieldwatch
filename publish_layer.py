"""上传 Layer 到阿里云函数计算 - 使用 requests"""
import base64
import json
import time
import hmac
import hashlib
import urllib.parse
import os
from pathlib import Path
import requests

# 凭证（从环境变量读取）
access_key_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID")
access_key_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
account_id = os.getenv("ALIBABA_CLOUD_ACCOUNT_ID")

if not all([access_key_id, access_key_secret, account_id]):
    print("错误: 缺少必要的环境变量")
    print("请设置: ALIBABA_CLOUD_ACCESS_KEY_ID, ALIBABA_CLOUD_ACCESS_KEY_SECRET, ALIBABA_CLOUD_ACCOUNT_ID")
    exit(1)

region = os.getenv("ALIBABA_CLOUD_REGION", "cn-shanghai")

print(f"AccountID: {account_id}")

# 读取 Layer zip 文件
layer_zip_path = Path(__file__).parent / 'layer' / 'python.zip'
with open(layer_zip_path, 'rb') as f:
    zip_content = f.read()

zip_base64 = base64.b64encode(zip_content).decode('utf-8')

# 创建 Layer 版本
layer_name = 'money-fund-monitor-deps'
print(f"\n正在上传 Layer: {layer_name}...")
print(f"文件大小: {len(zip_content) / 1024 / 1024:.2f} MB")

# 阿里云 FC API 签名
def sign(ak, aks, method, path, params, body=''):
    """生成阿里云 API 签名"""
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    # 1. 签名参数
    sorted_params = sorted(params.items())
    query_string = urllib.parse.urlencode(sorted_params)

    # 2. body
    if body:
        body_hash = hashlib.sha256(body.encode()).hexdigest()
    else:
        body_hash = hashlib.sha256(b'').hexdigest()

    # 3. 签名字符串
    string_to_sign = f'{method}\n{path}\n{query_string}\n{body_hash}\n{body_hash}\n{timestamp}'

    # 4. HMAC-SHA1
    signature = base64.b64encode(
        hmac.new(aks.encode(), string_to_sign.encode(), hashlib.sha1).digest()
    ).decode()

    return signature, timestamp

# API 请求
endpoint = f'https://{region}.fc.aliyuncs.com'
path = f'/services/{account_id}/layers/{layer_name}/versions'
url = endpoint + path

params = {
    'layerName': layer_name,
    'description': '货币基金监控系统依赖',
    'compatibleRuntime.1': 'python3.10',
}

body = json.dumps({
    'layerName': layer_name,
    'code': {
        'zipFile': zip_base64,
    },
    'description': '货币基金监控系统依赖',
    'compatibleRuntime': ['python3.10'],
})

signature, timestamp = sign(access_key_id, access_key_secret, 'POST', path, params, body)

headers = {
    'Content-Type': 'application/json',
    'x-fc-account-id': account_id,
    'x-fc-date': timestamp,
    'x-fc-signature': signature,
}

try:
    response = requests.post(
        url,
        headers=headers,
        data=body,
        params=params,
        timeout=300,
    )

    print(f"\n响应状态码: {response.status_code}")
    print(f"响应内容: {response.text[:500]}")

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"\nLayer 创建成功!")
        print(f"Layer ARN: {result.get('arn')}")
        print(f"Layer Version: {result.get('version')}")

        # 更新 s.yaml
        version = result.get('version')
        layer_arn = f"acs:{region}:{account_id}:{layer_name}:{version}"

        import yaml
        with open('s.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        if 'services' in config and 'money-fund-monitor' in config['services']:
            if 'function' in config['services']['money-fund-monitor']['props']:
                config['services']['money-fund-monitor']['props']['function']['layers'] = [layer_arn]

        with open('s.yaml', 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        print(f"\n已更新 s.yaml 中的 layer 配置: {layer_arn}")
    else:
        print(f"\n创建失败: {response.text}")

except Exception as e:
    print(f"\n错误: {e}")
    import traceback
    traceback.print_exc()
