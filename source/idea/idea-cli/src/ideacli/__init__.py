import click
import ideacli_meta

__version__ = ideacli_meta.__version__

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'], max_content_width=1200)


class CliContext(object):

    def __init__(self):
        self.verbosity = 0
        self.debug = False
        self.format = 'table'

    def as_dict(self):
        return {
            'verbosity': self.verbosity,
            'debug': self.debug,
            'format': self.format
        }


context = click.make_pass_decorator(CliContext, ensure=True)


def verbosity_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(CliContext)
        state.verbosity = value
        return value

    return click.option('-v', '--verbose', count=True,
                        expose_value=False,
                        help='Enables verbosity.',
                        callback=callback)(f)


def debug_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(CliContext)
        state.debug = value
        return value

    return click.option('--debug',
                        is_flag=True,
                        expose_value=False,
                        help='Enables mode',
                        callback=callback)(f)


def format_option(f):
    def callback(ctx, param, value):
        state = ctx.ensure_object(CliContext)
        if value:
            state.format = value
        return value

    return click.option('-f', '--format',
                        expose_value=False,
                        help='Output Format. One of [json, table]',
                        callback=callback)(f)


def common_options(include: list = None, exclude: list = None):
    def add_common_options(func):

        mandatory = {
            'format': format_option
        }

        optional = {
            'debug': debug_option,
            'verbosity': verbosity_option
        }

        for option in mandatory:
            if exclude:
                if option not in exclude:
                    func = mandatory[option](func)
            else:
                func = mandatory[option](func)

        if include:
            for option in include:
                func = optional[option](func)

        return func

    return add_common_options
