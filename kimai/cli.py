# -*- coding: utf-8 -*-

import atexit
import click
import tabulate
import datetime

from prompt_toolkit import prompt
from prompt_toolkit.completion import Completer, Completion
from fuzzyfinder import fuzzyfinder

from . import kimai, dates
from . import favorites as fav
from .models import Record
from .config import config, flush_config

# Ensure that the config gets flushed at the end of each execution.
atexit.register(flush_config, config)


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


def print_records(records):
    """Prints a list of record as a table"""

    def extract_record_row(record: Record):
        if record.end:
            end = record.end.strftime('%H:%M:%S')
        else:
            end = '-'

        duration = ':'.join(str(record.duration).split(':')[:2])

        return [
            record.id,
            record.start.strftime('%H:%M:%S'),
            end,
            duration,
            record.customer,
            record.project,
            record.task,
            record.comment
        ]

    headers = ['Id', 'Start Time', 'End Time', 'Duration', 'Customer', 'Project', 'Task', 'Comment']
    rows = [extract_record_row(r) for r in records]

    table = tabulate.tabulate(rows, headers, tablefmt="grid")
    click.echo(table)


def prompt_with_autocomplete(prompt_title, collection_name, resolve_title=True):
    cached_collection = config.get(collection_name, {})

    if not cached_collection:
        click.echo('Falling back to ids. If you want to have fuzzy '
                   'autocompletion , please run "kimai configure" first.')

        return prompt(prompt_title)

    title = None

    while title not in cached_collection:
        title = prompt(prompt_title, completer=FuzzyCompleter(cached_collection.keys()))

    if resolve_title:
        return cached_collection[title]

    return title


@click.group()
@click.version_option()
def cli():
    pass


@cli.command()
@click.option('--kimai-url', '-k', prompt='Kimai URL')
@click.option('--username', '-u', prompt='Username')
@click.option('--password', '-p', prompt='Password', hide_input=True)
@click.pass_context
def configure(ctx, kimai_url, username, password):
    """Configure the Kimai CLI"""
    config.set('KimaiUrl', kimai_url)

    r = kimai.authenticate(username, password)

    if not r.successful:
        print_error('Authentication failed.')
        return

    config.set('ApiKey', r.api_key)

    ctx.invoke(download_projects)
    ctx.invoke(download_tasks)

    print_success('Configuration complete')


@cli.command('stop')
@click.pass_context
def stop(ctx):
    """Stop the currently running record"""
    ctx.invoke(stop_record)


@cli.command('start')
@click.option('--task-id', '-t', type=int)
@click.option('--project-id', '-p', type=int)
@click.option('--favorite', '-f', type=str)
@click.option('--comment', '-c', type=str)
@click.pass_context
def start(ctx, task_id, project_id, favorite, comment):
    """Start a new record"""
    ctx.invoke(start_record, task_id=task_id, project_id=project_id, favorite=favorite, comment=comment)


@cli.command('comment')
@click.option('--comment', '-c',
              type=str, help='Providing a comment through this option overrides any existing comment')
def comment(comment):
    """Comment on the currently running record"""
    record_id = config.get('CurrentEntry')

    if not record_id:
        print_error('No record currently running')
        return

    if not comment:
        current_comment = config.get('Comment')
        comment = click.edit(current_comment)

    config.set('Comment', comment)


@cli.command('get-current')
@click.pass_context
def get_current(ctx):
    """Show the currently running record"""
    ctx.invoke(get_current_record)


@cli.command('today')
@click.pass_context
def today(ctx):
    """Show today's tracked records"""
    ctx.invoke(get_today)


@cli.group()
@click.pass_context
def projects(ctx):
    """Display and download projects from Kimai"""
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


@projects.command('download')
def download_projects():
    """Downloads all existing projects to disk so they can be used
    for autocompletion"""
    remote_projects = kimai.get_projects()

    project_map = {}

    for project in remote_projects:
        map_key = "(%s) %s" % (project['customerName'], project['name'])
        project_map[map_key] = project['projectID']

    config.set('Projects', project_map)
    print_success('Successfully downloaded projects.')


@cli.group()
@click.pass_context
def tasks(ctx):
    """Display and download tasks from Kimai"""
    if config.get('ApiKey') is None:
        print_error(
            'kimai-cli has not yet been configured. Use \'kimai configure\' first before using any other command'
        )
        ctx.abort()


@tasks.command('list')
def list_tasks():
    """Lists all available tasks"""
    print_table(kimai.get_tasks())


@tasks.command('download')
def download_tasks():
    """Downloads all existing tasks to disk so they can be used for autocompletion"""
    remote_tasks = kimai.get_tasks()

    task_map = {}

    for task in remote_tasks:
        task_map[task['name']] = task['activityID']

    config.set('Tasks', task_map)
    print_success('Successfully downloaded tasks.')


@cli.group()
@click.pass_context
def record(ctx):
    """Create/Update/Delete records"""
    if config.get('ApiKey') is None:
        print_error(
            '''kimai-cli has not yet been configured. Use \'kimai configure\'
            first before using any other command'''
        )
        ctx.abort()


@record.command('start')
@click.option('--task-id', '-t', type=int)
@click.option('--project-id', '-p', type=int)
@click.option('--favorite', '-f', type=str)
@click.option('--comment', '-c', type=str)
def start_record(task_id, project_id, favorite, comment):
    """Start a new time recording"""
    if not favorite and not (project_id and task_id):
        favorite = prompt_with_autocomplete('Favorite: ', 'Favorites', resolve_title=False)

    if favorite:
        try:
            favorite = fav.get_favorite(favorite)
            project_id = favorite.Project
            task_id = favorite.Task
        except RuntimeError as e:
            print_error(str(e))
            return

    response = kimai.start_recording(task_id, project_id)

    if response.successful:
        config.set('Comment', comment)
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
def get_current_record():
    """Get the currently running time recording."""
    current = kimai.get_current()

    if not current:
        return

    current.comment = config.get('Comment')

    print_records([current])


@record.command('get-today')
def get_today():
    """Returns all recorded entries for today"""
    records = kimai.get_todays_records()

    total = datetime.timedelta()
    for r in records:
        total += r.duration
    total = ':'.join(str(total).split(':')[:2])

    print_records(records)

    click.echo(click.style('Total: ', fg='green', bold=True) + total + 'h')


@record.command('add')
@click.option('--start-time', '-s', type=str)
@click.option('--end-time', '-e', type=str)
@click.option('--last-entry-id', '-l', type=int, help='ID of the last entry this record should snap to')
@click.option('--duration', '-d', type=str)
@click.option('--project-id', '-p', type=int)
@click.option('--task-id', '-t', type=int)
@click.option('--favorite', '-f', type=str)
@click.option('--comment', '-c', default='', type=str)
def add_record(start_time, end_time, last_entry_id, duration, favorite, project_id, task_id, comment):
    if not end_time and not duration:
        print_error('Need either an end time or a duration.')
        return

    if not favorite and not (project_id and task_id):
        favorite = prompt_with_autocomplete('Favorite: ', 'Favorites', resolve_title=False)

    if not (last_entry_id or start_time):
        print_error('Need either a start time or the id of the previous record.')
        return

    # If the id of the last record was provided, we assume that the start time of
    # this entry should be equal to the end time of the last entry. This allows
    # the user to "snap" entries together to easily fill gaps in the timesheet.
    if last_entry_id:
        last_entry = kimai.get_single_record(last_entry_id)

        if not last_entry:
            print_error('No record exists for id %s' % last_entry_id)
            return
        
        start_time = last_entry.end
    else:
        start_time = dates.parse(start_time)

    if start_time is None:
        print_error('Could not parse start date')
        return

    if duration:
        # We assume that any duration should be added to the start time
        # since it doesn't make sense to have the end time be before the
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

    if not comment:
        comment = click.edit('# Please enter a description of your activity')

    result = kimai.add_record(
        start_time,
        end_time,
        project_id,
        task_id,
        comment=comment
    )

    print_success(str(result.items[0]['id']))


@record.command('edit')
@click.option('--id', '-i', prompt="Record Id", type=int)
@click.option('--start-time', '-s', type=str)
@click.option('--end-time', '-e', type=str)
@click.option('--last-entry-id', '-l', type=int, help='ID of the last entry this record should snap to')
@click.option('--project-id', '-p', type=int)
@click.option('--task-id', '-t', type=int)
@click.option('--favorite', '-f', type=str)
@click.option('--comment', '-c', type=str)
def edit_record(id, start_time, end_time, last_entry_id, project_id, task_id, favorite, comment):
    """Edit a record"""
    if last_entry_id:
        try:
            last_entry = kimai.get_single_record(last_entry_id)
            start_time = last_entry.end
        except KeyError as e:
            print_error(str(e))
            return
    elif start_time:
        start_time = dates.parse(start_time)

    if end_time:
        end_time = dates.parse(end_time)

    if favorite:
        try:
            favorite = fav.get_favorite(favorite)
            project_id = favorite.Project
            task_id = favorite.Task
        except KeyError as e:
            print_error(str(e))
            return

    kimai.edit_record(
        id,
        start=start_time,
        end=end_time,
        task_id=task_id,
        project_id=project_id,
        comment=comment
    )

    print_success('Successfully updated record %s' % id)


@record.command('delete')
@click.option('--id', '-i', required=True, type=int, multiple=True)
def delete_record(id):
    for record_id in id:
        try:
            response = kimai.delete_record(record_id)
        except RuntimeError as e:
            print_error(str(e))
            continue

        if not response.successful:
            print_error(response.error)
        else:
            print_success('Record %s successfully deleted' % record_id)


@record.command('comment')
@click.option('--id', '-i', prompt="Id", type=int)
@click.option('--comment', '-c', type=str,
              help="When providing a comment through the cli you overwrite any comment that was already present")
def comment_on_record(id, comment):
    try:
        kimai.authorize_user(id)
    except RuntimeError as e:
        print_error(str(e))
        return

    record = kimai.get_single_record(id)

    if not record:
        print_error('No entry exists for id %s' % id)
        return

    if not comment:
        comment = click.edit(record.comment)

    kimai.comment_on_record(id, comment)


@cli.group()
@click.pass_context
def favorites(ctx):
    """Create and manage favorites"""
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
@click.option('--project-id', '-p', type=int)
@click.option('--task-id', '-t', type=int)
@click.option('--name', '-n', prompt='Favorite name', type=str)
def add_favorite(project_id, task_id, name):
    """Adds a favorite."""
    if not project_id:
        project_id = prompt_with_autocomplete('Project: ', 'Projects')

    if not task_id:
        task_id = prompt_with_autocomplete('Task: ', 'Tasks')

    try:
        fav.add_favorite(name, project_id, task_id)
    except RuntimeError as e:
        print_error(str(e))
        return

    print_success('Successfully added favorite "%s"' % name)


@favorites.command('delete')
@click.option('--name', '-n', type=str)
def delete_favorite(name):
    """Deletes a favorite"""
    if not name:
        name = prompt_with_autocomplete('Favorite: ', 'Favorites', resolve_title=False)

    fav.delete_favorite(name)
    print_success('Successfully removed favorite "%s"' % name)


@favorites.command('start')
@click.option('--name', '-n', type=str)
@click.option('--comment', '-c', type=str)
@click.pass_context
def start_recording_favorite(ctx, name, comment):
    if not name:
        name = prompt_with_autocomplete('Favorite: ', 'Favorites', resolve_title=False)

    try:
        favorite = fav.get_favorite(name)
    except RuntimeError as e:
        print_error(str(e))
        return

    ctx.invoke(
        start_record,
        task_id=favorite.Task,
        project_id=favorite.Project,
        comment=comment
    )


class FuzzyCompleter(Completer):
    def __init__(self, projects):
        self.projects = projects

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor(WORD=True)
        matches = fuzzyfinder(word_before_cursor, self.projects)
        for m in matches:
            yield Completion(m, start_position=-len(word_before_cursor))
