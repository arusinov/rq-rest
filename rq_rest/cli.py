import os
import sys
from string import Template

import click
from rq.cli.cli import main, pass_cli_config
from rq.cli import worker as rq_worker
from rq.defaults import (DEFAULT_CONNECTION_CLASS, DEFAULT_JOB_CLASS,
                         DEFAULT_QUEUE_CLASS, DEFAULT_WORKER_CLASS,
                         DEFAULT_RESULT_TTL, DEFAULT_WORKER_TTL,
                         DEFAULT_JOB_MONITORING_INTERVAL,
                         DEFAULT_LOGGING_FORMAT, DEFAULT_LOGGING_DATE_FORMAT)

from rq_rest.worker import workerFactory
from rq_rest.rest import restapp
from rq_rest import __version__ as version

main.params = []
main = click.version_option(version)(main)

@main.command()
@click.option('--burst', '-b', is_flag=True, help='Run in burst mode (quit after all work is done)')
@click.option('--logging_level', type=str, default="INFO", help='Set logging level')
@click.option('--log-format', type=str, default=DEFAULT_LOGGING_FORMAT, help='Set the format of the logs')
@click.option('--date-format', type=str, default=DEFAULT_LOGGING_DATE_FORMAT, help='Set the date format of the logs')
@click.option('--name', '-n', help='Specify a different name')
@click.option('--results-ttl', type=int, default=DEFAULT_RESULT_TTL, help='Default results timeout to be used')
@click.option('--worker-ttl', type=int, default=DEFAULT_WORKER_TTL, help='Default worker timeout to be used')
@click.option('--job-monitoring-interval', type=int, default=DEFAULT_JOB_MONITORING_INTERVAL, help='Default job monitoring interval to be used')
@click.option('--disable-job-desc-logging', is_flag=True, help='Turn off description logging.')
@click.option('--verbose', '-v', is_flag=True, help='Show more output')
@click.option('--quiet', '-q', is_flag=True, help='Show less output')
@click.option('--sentry-dsn', envvar='RQ_SENTRY_DSN', help='Report exceptions to this Sentry DSN')
@click.option('--exception-handler', help='Exception handler(s) to use', multiple=True)
@click.option('--pid', help='Write the process ID number to a file at the specified path')
@click.option('--disable-default-exception-handler', '-d', is_flag=True, help='Disable RQ\'s default exception handler')
@click.option('--max-jobs', type=int, default=None, help='Maximum number of jobs to execute')
@click.option('--with-scheduler', '-s', is_flag=True, help='Run worker with scheduler')
@click.option('--rest-token', '-t', type=str, envvar='RQ_REST_TOKEN',
              help='RQ-REST publishers access token'
                   '(if it is not set will be used simple RQ worker)')
@click.option('--rest-setting', multiple=True, type=str,
              help='RQ-REST worker setting in key=value format')
@click.argument('queue')
@pass_cli_config
@click.pass_context
def worker(ctx,
           cli_config, burst, logging_level, name, results_ttl,
           worker_ttl, job_monitoring_interval, disable_job_desc_logging, verbose, quiet, sentry_dsn,
           exception_handler, pid, disable_default_exception_handler, max_jobs, with_scheduler,
           queue, log_format, date_format,
           rest_token, rest_setting, **options):
    """Starting RQ-REST worker"""
    if rest_token:
        workerFactory.register(rest_token, *rest_setting)
    ctx.forward(rq_worker,
            queues=(queue,),
            queue_class='rq_rest.queue.RestQueue',
            worker_class='rq_rest.worker.Worker')


@main.command()
@click.option('--simple', is_flag=True, help='Run in development mode (simple server)')
@click.option('--host', '-h', type=str, default='0.0.0.0', envvar='RQ_REST_HOST',
              help='Listen on IP-address or hostname (default 0.0.0.0)')
@click.option('--port', '-p', type=int, default=8000, envvar='RQ_REST_PORT',
              help='Listen on port (default 8000)')
@click.option('--workers', '-w', type=int, default=2, envvar='RQ_REST_PROC',
              help='The number of worker processes for handling requests (default 2)')
@click.option('--wsgi-class', '-k', type=str, default='sync',
              help="The type of WSGI workers to use (default 'sync')")
@click.option('--debug', '-d', is_flag=True, help='Run with debug mode')
@pass_cli_config
@click.pass_context
def rest(ctx, cli_config, simple, host, port, workers, wsgi_class, debug, **options):
    """Starting RQ-REST HTTP Server"""
    sys.argv = [sys.argv[0]]
    restapp.config.update(**options)
    if simple:
        restapp.run(host=host, port=port, debug=True, reloader=False)
    else:
        restapp.run(host=host, port=port, debug=debug, reloader=False, server='gunicorn',
                    workers=workers, worker_class=wsgi_class, user=os.getuid())

@main.command()
@click.argument('service')
def build_service(service):
    """Build services for autostart RQ-REST workers and REST-server"""
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(sys.executable)))
    if service == 'rq-rest':
        rq_rest_service_src = os.path.join(CURRENT_DIR, 'systemd', 'rq-rest.tpl')
        with open(rq_rest_service_src, 'r') as tpl:
            service_tpl = Template(tpl.read())
            service = service_tpl.substitute(base_path=BASE_PATH)
        click.echo(service)
    elif service == 'rq-rest-worker':
        rq_rest_service_src = os.path.join(CURRENT_DIR, 'systemd', 'rq-rest-worker.tpl')
        with open(rq_rest_service_src, 'r') as tpl:
            service_tpl = Template(tpl.read())
            service = service_tpl.substitute(base_path=BASE_PATH)
        click.echo(service)


if __name__ == '__main__':
    main()
