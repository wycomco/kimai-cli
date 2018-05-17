import click
import tabulate
import kimai
import config
import dates
import favorites as fav

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from fuzzyfinder import fuzzyfinder


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


def prompt_with_autocomplete(prompt_title, collection_name, resolve_title=True):
    cached_collection = config.get(collection_name, {})

    if not cached_collection:
        click.echo('''No {} downloaded. Falling back to ids. If you 
        want to have autocompletion for cached_collection, please run 
        "kimai cached_collection download" first.''')

        return prompt('{} Id:'.format(prompt_title))

    title = None

    while title not in cached_collection:
        title = prompt(prompt_title, completer=FuzzyCompleter(cached_collection.keys()))

    if resolve_title:
        return cached_collection[title]

    return title


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


@record.command('get-today')
def get_today():
    """Returns all recorded entries for today"""
    records = kimai.get_todays_records()

    print_table(records, columns=[
        'timeEntryID',
        'start',
        'end',
        'customerName',
        'projectName',
        'activityName'
    ])


@record.command('add')
@click.option('--start-time', prompt="Start Time", type=str)
@click.option('--end-time', type=str)
@click.option('--duration', type=str)
@click.option('--project-id', type=int)
@click.option('--task-id', type=int)
@click.option('--favorite', type=str)
@click.option('--comment', default='', type=str)
def add_record(start_time, end_time, duration, favorite, project_id, task_id, comment):
    if not end_time and not duration:
        print_error('Need either an end time or a duration.')
        return

    if not favorite and not (project_id and task_id):
        print_error('Need either the name of a favorite or a task id and project id')
        return

    start_time = dates.parse(start_time)

    if start_time is None:
        print_error('Could not parse start date')
        return

    if duration:
        # We assume that any duration should be added to the start time
        # since it doesn't make sence to have the end time be before the
        # start time
        end_time = dates.parse('+' + duration, start_time)
    else:
        end_time = dates.parse(end_time)

    if end_time is None:
        print_error('Could not parse end date')
        return

    if favorite:
        try:
            favorite = fav.get_favorite(favorite)
            project_id = favorite.Project
            task_id = favorite.Task
        except RuntimeError as e:
            print_error(str(e))
            return

    response = kimai.add_record(
        start_time,
        end_time,
        project_id,
        task_id,
        comment=comment
    )


@record.command('delete')
@click.option('--id', prompt='Entry Id', type=int)
def delete_record(id):
    response = kimai.delete_record(id)

    if not response.successful:
        print_error(response.error)
    else:
        print_success('Record successfully deleted')


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
    try:
        favorite = fav.get_favorite(name)
    except RuntimeError as e:
        print_error(str(e))
        return

    ctx.invoke(
        start_record,
        task_id=favorite.Task,
        project_id=favorite.Project
    )


class FuzzyCompleter(Completer):
    def __init__(self, projects):
        self.projects = projects

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        matches = fuzzyfinder(word_before_cursor, self.projects)
        for m in matches:
            yield Completion(m, start_position=-len(word_before_cursor))
