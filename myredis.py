from configparser import ConfigParser
import redis

class RedisClient:
    def __init__(self):
        self.config = {}
        self._init_config()
        self.redis = self._connect()
        
    def _init_config(self):
        """初始化配置"""
        cf = ConfigParser()
        cf.read('redis-conf.ini')
        self.config = {
            'host' : cf.get('redis', 'host'),
            'port' : cf.get('redis', 'port'),
            'username' : cf.get('redis', 'username'),
            'password' : cf.get('redis', 'password'),
            'db' : cf.get('redis', 'db'),
        }
    def _connect(self):
        """连接redis"""
        try:
            pool = redis.ConnectionPool(
                host=self.config['host'],
                port=self.config['port'],
                username=self.config['username'],
                password=self.config['password'],
                db=self.config['db']
            )
            return redis.Redis(connection_pool=pool)
        except Exception as e:
            print(f'连接redis失败: {e}')
            raise e
    def get(self, key):
        """获取值"""
        try:
            value = self.redis.get(key);
            if isinstance(value, bytes):
                return value.decode('utf-8')
        except Exception as e:
            self._handle_error(e)
            print("get error")
            return None
    def set(self, key, value, expire=None):
        """设置值"""
        try:
            self.redis.set(key, value,ex=expire)
        except Exception as e:
            self._handle_error(e)
    @classmethod
    def _handle_error(cls, e):
        print(f'发生异常: {e}')
        raise e
