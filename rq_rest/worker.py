import os

import click
from rq.worker import Worker as RQWorker

from rq_rest.queue import RestQueue


class RestRQWorker(RQWorker):

    def __init__(self, *args, **kwargs):
        self._token = kwargs.pop('rest_token') if 'rest_token' in kwargs else {}
        self._options = kwargs.pop('rest_options') if 'rest_options' in kwargs else {}
        kwargs['queue_class'] = kwargs.get('queue_class') or 'rq_rest.queue.RestQueue'
        super().__init__(*args, **kwargs)

    def register_birth(self):
        super().register_birth()
        for queue in self.queues:
            if isinstance(queue, RestQueue):
                queue.clear_rest()
                with self.connection.pipeline() as p:
                    queue.register_rest_token(self._token, pipeline=p)
                    self.log.info("RQ-REST token for queue '{}' will be registered".format(
                        queue.name))

                    for key, value in self._options.items():
                        queue.register_rest_option(key, value, pipeline=p)
                        self.log.info("RQ-REST setting for queue '{}' will be registered: {} = {}".format(
                            queue.name, key, value))

                    p.execute()


class _WorkerFactory:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(_WorkerFactory, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        self._token = None
        self._options = dict()

    def _to_rest_setting(self, item: str):
        try:
            _queue, _setting, _value = item.split(':', maxsplit=2)
        except Exception as exc:
            click.echo("RQ-REST ERROR: Bad setting format: {}".format(item))
        else:
            self._queue_settings.setdefault(_queue, dict(publish_tokens=[]))
            if _setting == 'publish_token':
                self._queue_settings[_queue]['publish_tokens'].append(_value)
            else:
                self._queue_settings[_queue][_setting] = _value

    def rest_settings(self, *settings):
        for item in settings:
            self._to_rest_setting(item)
        return self

    def register(self, token, *settings):
        self._token = token
        env_settings = os.environ.get('RQ_REST_SETTINGS')
        if env_settings is not None:
            try:
                env_settings_list = env_settings.split(';')
            except Exception as exc:
                click.secho(
                    "RQ-REST WARNING: Environment variable 'RQ_REST_SETTINGS' has bad format, ignore it",
                    fg='blue'
                )
            else:
                env_settings_list.extend(settings)
                settings = env_settings_list

        for item in settings:
            try:
                key,value = item.split("=")
                key,value = key.strip(), value.strip()
                self._options[key] = value
            except Exception as exc:
                click.secho(
                    "RQ-REST WARNING: Setting '{}' has bad format, ignore it".format(item),
                    fg='blue'
                )

    def options(self, **kwargs):
        self._options.update(**kwargs)
        return self

    def __call__(self, *args, **kwargs):
        if self._token is not None:
            kwargs['rest_token'] = self._token
            kwargs['rest_options'] = self._options
            return RestRQWorker(*args, **kwargs)
        else:
            return RQWorker(*args, **kwargs)


Worker = _WorkerFactory()
workerFactory = Worker