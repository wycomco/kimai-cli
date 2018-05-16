import click
import requests
import json
import yaml
import os
import errno
import tabulate


KIMAI_URL = 'https://kimai.wycomco.de'
CONFIG_FOLDER = os.path.expanduser('~/.kimai')
CONFIG_PATH = os.path.join(CONFIG_FOLDER, 'config')


@click.group()
@click.pass_context
def cli(ctx):
    try:
        os.makedirs(CONFIG_FOLDER)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.load(f)
    except OSError as e:
        config = {}

    ctx.obj = config

@cli.command()
@click.argument('username')
@click.option('--password', prompt='Password', hide_input=True)
@click.pass_context
def auth(ctx, username, password):
    """Authenticate against the Kimai backend to retrieve an api key. This method only
    needs to be called once.
    """

    payload = '{"jsonrpc":"2.0", "method":"authenticate", "params":["%s","%s"], "id":"1"}' % (username, password)
    r = KimaiAuthResponse(requests.post('{}/core/json.php'.format(KIMAI_URL), data=payload))

    if not r.success:
        click.echo(click.style('Could not authenticate against Kimai backend.', fg='red'), err=True)
        return

    with open(CONFIG_PATH, 'w') as outfile:
        yaml.dump({'ApiKey': r.apiKey}, outfile, default_flow_style=False)

    click.echo(click.style('Successfully authenticated.', fg='green'))


@cli.group()
@click.pass_context
def projects(ctx):
    if 'ApiKey' not in ctx.obj:
        click.echo(click.style('Not yet authenticated. Use \'kimai auth\' first before using any other command', fg='red'), err=True)
        ctx.abort()


@projects.command()
@click.pass_obj
def list(config):
    payload = '{"jsonrpc":"2.0", "method":"getProjects", "params":["%s"], "id":"1234"}' % (config['ApiKey'])
    r = requests.post('{}/core/json.php'.format(KIMAI_URL), data=payload)
    projects = json.loads(r.text)['result']['items']
    click.echo(tabulate.tabulate(projects, headers='keys'))


class KimaiAuthResponse(object):
    def __init__(self, response):
        self.data = json.loads(response.text)['result']

    @property
    def success(self):
        return self.data['success']

    @property
    def apiKey(self):
        if not self.success:
            raise RuntimeError('Invalid credentials')
        return self.data['items'][0]['apiKey']
