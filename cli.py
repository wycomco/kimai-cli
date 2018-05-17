import click
import tabulate
import kimai
import config
import favorites as fav


def print_success(message):
    """Print success message to the console."""
    click.echo(click.style(message, fg='green'))


def print_error(message):
    """Print error message to the console."""
    click.echo(click.style(message, fg='red'), err=True)


def print_table(rows, columns=None):
    """Print a table to the console."""
    if columns is not None:
        rows = map(lambda r: {k: r[k] for k in columns if k in r}, rows)
    click.echo(tabulate.tabulate(rows, headers='keys', tablefmt="grid"))


@click.group()
def cli():
    pass


@cli.command()
@click.option('--kimai-url', prompt='Kimai URL')
@click.option('--username', prompt='Username')
@click.option('--password', prompt='Password', hide_input=True)
def configure(kimai_url, username, password):
    """Configure the Kimai-CLI"""
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
    """Lists all available projects"""
    print_table(
        kimai.get_projects(),
        columns=['projectID', 'name', 'customerName'],
    )


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
    """Lists all available tasks"""
    print_table(kimai.get_tasks())


@cli.group()
@click.pass_context
def record(ctx):
    if config.get('ApiKey') is None:
        print_error(
            '''kimai-cli has not yet been configured. Use \'kimai configure\'
            first before using any other command'''
        )
        ctx.abort()


@record.command('start')
@click.option('--task-id', prompt='Task Id', type=int)
@click.option('--project-id', prompt='Project Id', type=int)
def start_record(task_id, project_id):
    """Start a new time recording"""
    response = kimai.start_recording(task_id, project_id)

    if response.successful:
        print_success(
            'Started recording. To stop recording type \'kimai record stop\''
        )
    else:
        print_error('Could not start recording: "%s"' % response.error)


@record.command('stop')
def stop_record():
    """Stops the currently running recording (if there is one)"""
    response = kimai.stop_recording()

    if not response:
        print_success('No recording running.')
        return

    if response.successful:
        print_success('Stopped recording.')
    else:
        print_error('Could not stop recording: "%s"' % response.error)


@record.command('get-current')
def get_current():
    """Get the currently running time recording."""
    current = kimai.get_current()

    if not current:
        return

    print_table([current], columns=[
        'timeEntryID',
        'start',
        'end',
        'customerName',
        'projectName',
        'activityName'
    ])


@cli.group()
@click.pass_context
def favorites(ctx):
    if config.get('ApiKey') is None:
        print_error(
            '''kimai-cli has not yet been configured. Use \'kimai configure\'
            first before using any other command'''
        )
        ctx.abort()


@favorites.command('list')
def list_favorites():
    """List all favorites"""
    print_table(fav.list_favorites())


@favorites.command('add')
@click.option('--project-id', prompt='Project Id', type=int)
@click.option('--task-id', prompt='Task Id', type=int)
@click.option('--name', prompt='Favorite name', type=str)
def add_favorite(project_id, task_id, name):
    """Adds a favorite."""
    try:
        fav.add_favorite(name, project_id, task_id)
    except RuntimeError as e:
        print_error(e.message)
        return

    print_success('Successfully added favorite "%s"' % name)


@favorites.command('delete')
@click.option('--name', prompt='Favorite name', type=str)
def delete_favorite(name):
    """Deletes a favorite"""
    fav.delete_favorite(name)
    print_success('Successfully removed favorite "%s"' % name)


@favorites.command('start')
@click.option('--name', prompt='Favorite name', type=str)
@click.pass_context
def start_recording_favorite(ctx, name):
    favorite = fav.get_favorite(name)

    if not favorites:
        return

    ctx.invoke(
        start_record,
        task_id=favorite.Task,
        project_id=favorite.Project
    )
