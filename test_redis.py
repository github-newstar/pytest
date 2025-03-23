from myredis import RedisClient

redis_client = RedisClient()
redis_client.set('name', 'zhangsan', expire=300)
value = redis_client.get('name')
print(f"获取到的值: {value}")