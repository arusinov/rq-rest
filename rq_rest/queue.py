from typing import Any

from rq.connections import resolve_connection
from rq.queue import Queue

def decode_list(src_list):
    normilized_list = []
    for item in src_list:
        if isinstance(item, bytes):
            item = item.decode(encoding='utf-8', errors='ignore')
        normilized_list.append(item)
    return normilized_list

def decode_dict(src_dict):
    normilized_dict = dict()
    for key, value in src_dict.items():
        if isinstance(key, bytes):
            key = key.decode(encoding='utf-8')
        if isinstance(value, bytes):
            try:
                value = value.decode(encoding='utf-8')
            except Exception as exc:
                pass
        if isinstance(value, (list, tuple, set)):
            value = decode_list(value)
        normilized_dict[key] = value
    return normilized_dict


class RestQueue(Queue):

    redis_rest_settings_namespace_prefix = 'rq-rest:settings:'
    redis_rest_tokens_namespace_prefix = 'rq-rest:tokens:'

    def __init__(self, name='default', default_timeout=None, connection=None, is_async=True, job_class=None, **kwargs):
        super().__init__(name, default_timeout, connection, is_async, job_class, **kwargs)
        self.__settings_cache = None

    @property
    def rest_settings_key(self) -> str:
        return self.redis_rest_settings_namespace_prefix + self.name

    @property
    def rest_tokens_key(self) -> str:
        return self.redis_rest_tokens_namespace_prefix + self.name

    def register_rest_token(self, token: str, pipeline=None):
        connection = pipeline if pipeline is not None else self.connection
        connection.sadd(self.rest_tokens_key, token)

    def revoke_rest_token(self, token: str,  pipeline=None):
        connection = pipeline if pipeline is not None else self.connection
        connection.srem(self.rest_tokens_key, token)

    @property
    def rest_tokens(self) -> list:
        return self.connection.smembers(self.rest_tokens_key)

    def set_setting(self, key: str, value: Any, pipeline=None):
        connection = pipeline if pipeline is not None else self.connection
        connection.hset(self.rest_settings_key, key, value)

    def register_rest_option(self, key: str, value: Any, pipeline=None):
        connection = pipeline if pipeline is not None else self.connection
        connection.hset(self.rest_settings_key, key, value)

    def get_setting(self, key: str, default: Any=None) -> Any:
        return self.connection.hget(self.rest_settings_key, key) or default

    @property
    def rest_settings(self) -> dict:
        if not self.__settings_cache:
            self.__settings_cache = decode_dict(self.connection.hgetall(self.rest_settings_key))
        return self.__settings_cache

    def refresh_rest(self):
        self.__settings_cache = None

    def clear_rest(self):
        self.connection.delete(self.rest_tokens_key, self.rest_settings_key)
        self.refresh_rest()

    def is_rest(self):
        return bool(self.rest_tokens or self.rest_settings)

    @classmethod
    def from_name(cls, queue_name, connection = None):
        connection = resolve_connection(connection)
        queue = RestQueue(queue_name, connection=connection)
        return queue if queue.is_rest() else None
