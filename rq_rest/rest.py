import functools
import json
from datetime import timedelta

from bottle import Bottle, request, HTTPError, HTTPResponse
from redis import Redis
from rq import Queue

from .defaults import DEFAULT_JOB_PREFIX, DEFAULT_JOB_TYPE
from .queue import RestQueue


def with_redis(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            redis_url = request.app.config.get('url', 'redis://localhost')
            connection = Redis.from_url(redis_url)
            connection.ping()
            setattr(request, 'redis', connection)
        except Exception as exc:
            raise HTTPError(500, 'Redis connection problem: {}'.format(exc))
        return func(*args, **kwargs)

    return wrapper


def parse_request_data(request):
    data = request.json or {}
    if not data:
        for key in request.params:
            values = request.params.getlist(key)
            if len(values) > 1:
                data[key] = values
            else:
                data[key] = values[0]
    return data


def authenticate_request(request, queue):
    if queue.rest_tokens:
        request_token = None
        if 'X-API-Key' in request.headers:
            request_token = request.headers.get('X-API-Key')
        elif request.get_cookie('api_key'):
            request_token = request.get_cookie('api_key')
        else:
            request_data = parse_request_data(request)
            if 'api_key' in request_data:
                request_token = request_data.get('api_key')

        if request_token is None:
            return False
        else:
            if not isinstance(request_token, bytes):
                request_token = bytes(request_token, encoding='utf-8')
            return request_token in queue.rest_tokens

    return True

@with_redis
def queue_settings(queue):
    rest_queue = RestQueue.from_name(queue, connection=request.redis)
    if not rest_queue:
        raise HTTPError(404, 'RestQueue is not found')
    if not authenticate_request(request, rest_queue):
        raise HTTPError(401, 'Unauthorized')
    return rest_queue.rest_settings

@with_redis
def create_job(queue):
    rest_queue = RestQueue.from_name(queue, connection=request.redis)
    if not rest_queue:
        raise HTTPError(404, 'RestQueue is not found')
    if not authenticate_request(request, rest_queue):
        raise HTTPError(401, 'Unauthorized')

    job_data = parse_request_data(request)
    if 'api_key' in job_data:
        job_data.pop('api_key')

    option_params = ('ttl', 'result_ttl', 'failure_ttl', 'id', 'description', 'timeout')
    options = dict()
    for key in option_params:
        if key in job_data:
            options[key] = job_data.pop(key)
        elif key in rest_queue.rest_settings:
            options[key] = rest_queue.rest_settings[key]

    short_job_type = job_data.pop('job_type') if 'job_type' in job_data else DEFAULT_JOB_TYPE
    job_prefix = rest_queue.rest_settings.get('prefix') or "{}.tasks.".format(rest_queue.name)
    job_type = "{}{}".format(job_prefix, short_job_type)

    try:
        delay = int(job_data.pop('delay'))
    except Exception as exc:
        delay = 0

    if delay:
        job = rest_queue.enqueue_in(timedelta(seconds=delay), job_type, kwargs=job_data, **options)
    else:
        options.update(job_data)
        job = rest_queue.enqueue(job_type, **options)
    return {
        'queue': rest_queue.name,
        'type': job_type,
        'id': job.id,
        'status': job.get_status(),
    }


@with_redis
def job_resource(queue, job_id):
    rest_queue = RestQueue.from_name(queue, connection=request.redis)
    if not rest_queue:
        raise HTTPError(404, 'RestQueue is not found')
    if not authenticate_request(request, rest_queue):
        raise HTTPError(401, 'Unauthorized')
    job = rest_queue.fetch_job(job_id)
    if not job:
        raise HTTPError(404, 'Job is not found')

    if request.method == 'DELETE':
        for item in ('finished_job_registry', 'failed_job_registry', 'scheduled_job_registry'):
            registry = getattr(rest_queue, item)
            if job.id in registry.get_job_ids():
                registry.remove(job.id, delete_job=True)
                return HTTPResponse(status=204)
        raise HTTPError(400, 'Job in progress or deferred, cant delete')

    else:
        job_info = {
            'queue': rest_queue.name,
            'type': job.get_call_string(),
            'id': job_id,
            'status': job.get_status()
        }
        if job.result is not None:
            job_info['result'] = job.result
        if job.is_failed:
            job_info['error'] = str(job.exc_info)

        return job_info


class JSONErrorBottle(Bottle):

    def default_error_handler(self, res):
        res.content_type = 'application/json'
        return json.dumps(dict(error=res.body, status_code=res.status_code))


def create_rest_app():
    app = JSONErrorBottle()
    app.route('/<queue>/settings/', ('GET',), queue_settings)
    app.route('/<queue>/job/', ('POST', ), create_job)
    app.route('/<queue>/job/<job_id>/', ('GET', 'DELETE'), job_resource)
    return app


restapp = create_rest_app()




