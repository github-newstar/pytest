from configparser import ConfigParser
from myredis import RedisClient
import requests
import json
import time
import random
import threading
import pymysql  # 添加pymysql库

#配置
cf = ConfigParser()
cf.read('api_conf.ini')
base_url = cf.get('host','docker_url')
code_prefix = "code_"

num_users = 1000
test_duration = 60
report_interval = 5

# 并发控制
register_max_concurrent = 15  # 注册最大并发数
login_max_concurrent = 20     # 登录最大并发数
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
            time.sleep(random.uniform(0.05, 0.1))
            
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
    threads = []
    
    for i in range(num_users):
        thread = threading.Thread(target=user_workflow, args=(i,))
        threads.append(thread)
        thread.start()
        # 减少线程启动延迟
        time.sleep(0.05)  # 从0.1减少到0.05

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
    
    # 测试完成后重置数据库
    reset_database()

# 在脚本中添加阶梯式负载测试
def step_load_test():
    results = []
    # 测试不同并发级别
    concurrency_levels = [5, 10, 20, 30, 50 , 75, 100]
    step_test_duration = 60  # 增加到30秒，给系统更多稳定时间
    step_users = 500 # 增加到500用户以产生更多负载
    
    for concurrency in concurrency_levels:
        print(f"\n===== 开始测试并发数 {concurrency} =====")
        
        # 修改并发数
        global register_max_concurrent, login_max_concurrent, register_semaphore, login_semaphore
        register_max_concurrent = concurrency
        login_max_concurrent = concurrency
        register_semaphore = threading.Semaphore(register_max_concurrent)
        login_semaphore = threading.Semaphore(login_max_concurrent)
        
        # 重置统计
        global registration_successes, registration_failures, login_successes, login_failures, request_latencies
        global start_time, num_users, test_duration
        
        # 保存原始值
        original_users = num_users
        original_duration = test_duration
        
        # 设置阶梯测试参数
        num_users = step_users
        test_duration = step_test_duration
        
        # 重置统计数据
        registration_successes = 0
        registration_failures = 0
        login_successes = 0
        login_failures = 0
        request_latencies = []
        
        # 重置数据库，确保从干净状态开始
        reset_database()
        
        # 等待系统完全准备好
        time.sleep(1)
        
        # 运行当前并发级别测试
        start_time = time.time()
        
        # 修改为更有针对性的测试方法
        run_concurrent_test(concurrency)
        
        # 获取测试结果
        elapsed_time = time.time() - start_time
        total_requests = registration_successes + registration_failures + login_successes + login_failures
        rps = total_requests / elapsed_time if total_requests > 0 else 0
        
        # 安全计算平均延迟，确保不会出现负值
        if request_latencies:
            # 过滤掉异常值
            filtered_latencies = [lat for lat in request_latencies if lat > 0]
            if filtered_latencies:
                avg_latency = sum(filtered_latencies) / len(filtered_latencies) * 1000
            else:
                avg_latency = 0
        else:
            avg_latency = 0
            
        success_rate = (registration_successes + login_successes) / (total_requests) * 100 if total_requests > 0 else 0
        
        # 记录结果
        results.append({
            "concurrency": concurrency,
            "rps": rps,
            "latency": avg_latency,
            "success_rate": success_rate,
            "total_requests": total_requests
        })
        
        # 输出当前级别结果
        print(f"\n===== 并发数 {concurrency} 测试结果 =====")
        print(f"总请求数: {total_requests}")
        print(f"每秒请求数 (RPS): {rps:.2f}")
        print(f"平均请求延迟: {avg_latency:.2f} 毫秒")
        print(f"成功率: {success_rate:.2f}%")
        
        # 恢复原始值
        num_users = original_users
        test_duration = original_duration
    
    # 显示所有测试结果比较
    print("\n\n===== 阶梯测试结果比较 =====")
    print("并发数\t总请求\tRPS\t延迟(ms)\t成功率(%)")
    for result in results:
        print(f"{result['concurrency']}\t{result['total_requests']}\t{result['rps']:.2f}\t{result['latency']:.2f}\t{result['success_rate']:.2f}")
    
    # 找出最佳并发数（基于RPS最高且成功率在可接受范围内）
    valid_results = [r for r in results if r['success_rate'] > 90]
    if valid_results:
        best_result = max(valid_results, key=lambda x: x['rps'])
        print(f"\n推荐最佳并发数: {best_result['concurrency']} (RPS: {best_result['rps']:.2f}, 成功率: {best_result['success_rate']:.2f}%)")
    else:
        print("\n未找到满足条件的并发级别（成功率>90%）")

# 添加专门的并发测试函数，更好地控制并发性
def run_concurrent_test(concurrency):
    global registration_successes, registration_failures, login_successes, login_failures, request_latencies
    global start_time, num_users
    
    active_threads = []
    max_threads = concurrency * 3  # 保持足够的线程以维持所需并发度
    
    print(f"启动并发测试，目标并发度: {concurrency}")
    
    # 创建足够的线程池
    for i in range(num_users):
        while len(active_threads) >= max_threads:
            # 清理已完成的线程
            active_threads = [t for t in active_threads if t.is_alive()]
            time.sleep(0.01)
        
        # 创建新线程
        thread = threading.Thread(target=user_workflow, args=(i,))
        thread.daemon = True  # 设为守护线程，主线程结束时自动退出
        active_threads.append(thread)
        thread.start()
        
        # 动态调整线程创建速率，以维持目标并发度
        if len(active_threads) < concurrency:
            # 如果活动线程少于目标并发度，快速创建新线程
            time.sleep(0.01)
        else:
            # 如果达到目标并发度，等待更长时间
            time.sleep(0.1)
            
        # 检查是否达到测试时间
        if time.time() - start_time >= test_duration:
            break
            
    # 等待测试时间结束
    remaining_time = test_duration - (time.time() - start_time)
    if remaining_time > 0:
        print(f"等待剩余测试时间: {remaining_time:.2f}秒")
        time.sleep(remaining_time)
    
    # 等待活动线程完成（最多等待5秒）
    wait_end = time.time() + 5
    while active_threads and time.time() < wait_end:
        active_threads = [t for t in active_threads if t.is_alive()]
        if active_threads:
            print(f"等待剩余 {len(active_threads)} 个线程完成...")
            time.sleep(1)

if __name__ == "__main__":
    # 添加命令行参数支持
    import sys
    
    # 确保开始测试前数据库是干净的
    reset_database()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "step":
            print("开始阶梯式负载测试...")
            step_load_test()
        elif sys.argv[1] == "regular":
            print("开始标准压力测试...")
            pressure_test()
        else:
            print(f"未知参数: {sys.argv[1]}")
            print("用法: python net_test.py [step|regular]")
    else:
        print("开始阶梯式负载测试...")
        step_load_test()
