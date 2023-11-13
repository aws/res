import sys
import click
import ideacli


@click.group(context_settings=ideacli.CONTEXT_SETTINGS)
@click.version_option(version=ideacli.__version__)
def main():
    """
    IDEA CLI
    """
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
