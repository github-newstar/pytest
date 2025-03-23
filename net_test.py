from configparser import ConfigParser
from myredis import RedisClient
import pymysql
import requests
import json
import time
import random
import threading


#配置
cf = ConfigParser()
cf.read('api_conf.ini')
base_url = cf.get('host','local_url')
code_prefix = "code_"
# MySQL数据库连接配置
mysql_config = {
    'host': 'mq',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'chatdb',
    'charset': 'utf8mb4'
}

# 重置数据库函数
def reset_database():
    try:
        conn = pymysql.connect(**mysql_config)
        with conn.cursor() as cursor:
            # 清空用户表
            cursor.execute("TRUNCATE TABLE user")
            # 插入管理员用户
            cursor.execute("INSERT INTO user (uid, name, email, pwd) VALUES (1, 'admin', 'admin@localhost', 'admin')")
            conn.commit()
            print("数据库已重置")
    except Exception as e:
        print(f"数据库重置失败: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()


num_users = 100
test_duration = 60
report_interval = 5

# 并发控制
register_max_concurrent = 8 # 注册最大并发数
login_max_concurrent =  8   # 登录最大并发数
register_semaphore = threading.Semaphore(register_max_concurrent)
login_semaphore = threading.Semaphore(login_max_concurrent)

# 统计信息
registration_successes = 0
registration_failures = 0
login_successes = 0
login_failures = 0
request_latencies = []

start_time = time.time()
last_report_time = start_time

#启动redis客户端
redis_client = RedisClient()

# 生成随机邮箱
def generate_random_email(i: int):
    return f"testuser{i}@example.com"

# 生成随机用户名
def generate_random_username(i: int):
    return f"testuser{i}"

# 生成固定密码
def generate_password():
    return "00000000"

# 获取验证码接口 - 不限制并发
def get_code(email):
    varify_service = cf.get('apis','varify_service')
    url = f"{base_url}/{varify_service}"
    payload = json.dumps({"email" : email})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return False

# 从redis中获取验证码
def get_varify_code_from_redis(email):
    code = redis_client.get(code_prefix +email)
    return code

# 注册用户 - 限制并发
def register_user(email, username, password, code):
    global registration_successes, registration_failures, request_latencies
    with register_semaphore:  # 使用注册信号量控制并发
        user_register = cf.get('apis','user_register')
        url = f"{base_url}/{user_register}"
        payload = json.dumps({
            "email": email,
            "user": username,
            "passwd": password,
            "confirm": password,
            "varifycode": code
        })
        headers = {'Content-Type': 'application/json'}
        start = time.time()
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            if response.json().get("error") == 0:
                registration_successes += 1
                request_latencies.append(time.time() - start)
                return True
            else:
                registration_failures += 1
                # print(f"注册失败: {response.json()}")
                return False
        except requests.exceptions.RequestException as e:
            registration_failures += 1
            # print(f"注册请求失败: {e}")
            return False

# 登录用户 - 限制并发
def login_user(email, password):
    global login_successes, login_failures, request_latencies
    with login_semaphore:  # 使用登录信号量控制并发
        login = cf.get('apis','login')
        url = f"{base_url}/{login}"
        payload = json.dumps({
            "email": email,
            "passwd": password
        })
        headers = {'Content-Type': 'application/json'}
        start = time.time()
        try:
            response = requests.post(url, headers=headers, data=payload)
            response.raise_for_status()
            if response.json().get("error") == 0:
                login_successes += 1
                request_latencies.append(time.time() - start)
                return True
            else:
                login_failures += 1
                # print(f"登录失败: {response.json()}")
                return False
        except requests.exceptions.RequestException as e:
            login_failures += 1
            # print(f"登录请求失败: {e}")
            return False

def user_workflow(i):
    global login_successes, login_failures, request_latencies
    email = generate_random_email(i)
    username = generate_random_username(i)
    password = generate_password()

    # 获取验证码 - 不限制并发
    if get_code(email):
        # 从 Redis 获取验证码
        verification_code = get_varify_code_from_redis(email)
        if verification_code:
            # 注册用户 (并发已在函数内控制)
            register_result = register_user(email, username, password, verification_code)
            
            # 在注册和登录之间添加随机延迟
            time.sleep(random.uniform(0.1, 0.2))
            
            # 登录用户 (并发已在函数内控制)
            if register_result:
                login_user(email, password)
                
            # print(f"用户 {email} 处理完成")
        else:
            print(f"用户 {email} 未找到验证码")
    else:
        login_failures += 1
        # print(f"用户 {email} 获取验证码失败") 

def pressure_test():
    global last_report_time
    reset_database()
    threads = []
    
    for i in range(num_users):
        thread = threading.Thread(target=user_workflow, args=(i,))
        threads.append(thread)
        thread.start()
        # 减少线程启动延迟
        time.sleep(0.1)  # 从0.1减少到0.05

    while time.time() - start_time < test_duration:
        time.sleep(report_interval)
        elapsed_time = time.time() - start_time
        requests_count = registration_successes + registration_failures + login_successes + login_failures
        if requests_count > 0:
            requests_per_second = requests_count / elapsed_time
        else:
            requests_per_second = 0

        avg_latency = sum(request_latencies) / len(request_latencies) * 1000 if request_latencies else 0

        print(f"[{elapsed_time:.2f}s] 完成注册: {registration_successes}/{num_users}, 注册失败: {registration_failures}, 完成登录: {login_successes}/{num_users}, 登录失败: {login_failures}, RPS: {requests_per_second:.2f}, 平均延迟: {avg_latency:.2f} ms")
        last_report_time = time.time()

    for thread in threads:
        thread.join()

    # 输出最终报告
    elapsed_time = time.time() - start_time
    total_requests = registration_successes + registration_failures + login_successes + login_failures
    if total_requests > 0:
        final_rps = total_requests / elapsed_time
    else:
        final_rps = 0
    avg_latency = sum(request_latencies) / len(request_latencies) * 1000 if request_latencies else 0

    print("\n压力测试报告:")
    print(f"测试总时长: {elapsed_time:.2f} 秒")
    print(f"尝试注册用户数: {num_users}")
    print(f"注册成功数: {registration_successes}")
    print(f"注册失败数: {registration_failures}")
    print(f"尝试登录用户数: {num_users}")
    print(f"登录成功数: {login_successes}")
    print(f"登录失败数: {login_failures}")
    print(f"总请求数: {total_requests}")
    print(f"平均每秒请求数 (RPS): {final_rps:.2f}")
    print(f"平均请求延迟: {avg_latency:.2f} 毫秒")

if __name__ == "__main__":
    pressure_test()
