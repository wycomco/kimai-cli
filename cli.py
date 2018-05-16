import click
import tabulate
import kimai
import config


def print_success(message):
    """Print success message to the console."""
    click.echo(click.style(message, fg='green'))


def print_error(message):
    """Print error message to the console."""
    click.echo(click.style(message, fg='red'), err=True)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--kimai-url', prompt='Kimai URL')
@click.option('--username', prompt='Username')
@click.option('--password', prompt='Password', hide_input=True)
def configure(kimai_url, username, password):
    config.set('KimaiUrl', kimai_url)

    r = kimai.authenticate(username, password)

    if not r.successful:
        print_error('Authentication failed.')
        return

    config.set('ApiKey', r.apiKey)

    print_success('Configuration complete')


@cli.group()
@click.pass_context
def projects(ctx):
    if config.get('ApiKey') is None:
        print_error(
            '''kimai-cli has not yet been configured. Use \'kimai configure\'
            first before using any other command'''
        )
        ctx.abort()


@projects.command('list')
def list_projects():
    projects = kimai.get_projects()
    click.echo(tabulate.tabulate(projects, headers='keys'))


@cli.group()
@click.pass_context
def tasks(ctx):
    if config.get('ApiKey') is None:
        print_error(
            '''kimai-cli has not yet been configured. Use \'kimai configure\'
            first before using any other command'''
        )
        ctx.abort()


@tasks.command('list')
def list_tasks():
    tasks = kimai.get_tasks()
    click.echo(tabulate.tabulate(tasks, headers='keys'))


@cli.group()
@click.pass_context
def record(ctx):
    if config.get('ApiKey') is None:
        print_error(
            '''kimai-cli has not yet been configured. Use \'kimai configure\'
            first before using any other command'''
        )
        ctx.abort()


@record.command()
@click.option('--task-id', prompt='Task Id', type=int)
@click.option('--project-id', prompt='Project Id', type=int)
def start(task_id, project_id):
    """Start a new time recording"""
    response = kimai.start_recording(task_id, project_id)

    if response.successful:
        print_success('Started recording. To stop recording type \'kimai record stop\'')
    else:
        print_error('Could not start recording: "%s"' % response.error)


@record.command()
def stop():
    """Stops the currently running recording"""
    response = kimai.stop_recording()

    if response.successful:
        print_success('Stopped recording.')
    else:
        print_error('Could not stop recording: "%s"' % response.error)


@record.command('get-current')
def get_current():
    """Get the currently running time recording."""
    click.echo(tabulate.tabulate([kimai.get_current()], headers='keys'))