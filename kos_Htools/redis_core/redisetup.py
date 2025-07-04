import json
import logging
from typing import Dict, List, Any
from redis import Redis

logger = logging.getLogger(__name__)

class RedisBase:
    def __init__(
            self, 
            key: str, 
            data: Dict | List, 
            redis_client: Redis = None,
        ):
        self.redis = redis_client or Redis()
        self.key = key
        self.data = data
    
    def cached(self, data: Dict | List, ex: int | None = None) -> None:   
        if isinstance(data, (dict, list)):
            data = json.dumps(data)
            
        try:
            self.redis.set(name=self.key, value=data, ex=ex)
        except Exception as e:
            logger.error(f'Ошибка в redis: {e}')
    
    def get_default_value(self, data_type: type) -> Dict | List:
        return {} if data_type == dict else []
    
    def get_cached(self, data_type: type | None = None) -> Dict | List | str | bytes:
        data_type = data_type or type(self.data)
        result = self.get_default_value(data_type)

        try:
            cached_data = self.redis.get(self.key)
            if not cached_data:
                logger.warning(f'Ключ не найден: {self.key}')
                return result

            if isinstance(cached_data, bytes):
                cached_data = cached_data.decode('utf-8')

            if data_type in (dict, list):
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    logger.error(f'Ошибка декодирования JSON для ключа: {self.key}')
                    return result
            else:
                return cached_data
            
        except Exception as e:
            logger.error(f'Ошибка получения данных: {e}')
            return result   

    def delete_key(self) -> None:
        try:
            self.redis.delete(self.key)
        except Exception as e:
            logger.error(f'Ошибка удаления ключа {self.key}: {e}')
    
    def check_key_list(self) -> bool:
        if self.redis.exists(self.key):
            return self.redis.type(self.key) == 'list'
        else:
            return False
    
    @staticmethod
    def decode_list_item(l: list) -> list:
        return [item.decode('utf-8') if isinstance(item, bytes) else item for item in l]

class RedisShortened(RedisBase):
    def lpush(self, *values):
        return self.redis.lpush(self.key, *values)

    def rpush(self, *values):
        return self.redis.rpush(self.key, *values)

    def lpop(self):
        return self.redis.lpop(self.key)

    def rpop(self):
        return self.redis.rpop(self.key)

    def lrange(self, start, end, decode: bool = True):
        if not self.check_key_list():
            raise ValueError(f'Ключ {self.key} не является списком')
        
        result = self.redis.lrange(self.key, start, end)
        if decode:
            return self.decode_list_item(result)
        return result

    def llen(self):
        if not self.check_key_list():
            raise ValueError(f'Ключ {self.key} не является списком')
        
        return self.redis.llen(self.key)

    def lrem(self, count: int, value: str):
        if not self.check_key_list():
            raise ValueError(f'Ключ {self.key} не является списком')
        
        return self.redis.lrem(self.key, count, value)
    