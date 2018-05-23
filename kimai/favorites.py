# -*- coding: utf-8 -*-

from .config import config


def list_favorites():
    """Lists all saved favorites"""
    favorites = config.get('Favorites', {})
    tuples = [(name, favorites[name]['Project'], favorites[name]['Task']) for name in favorites]
    return [Favorite(*t) for t in tuples]


def get_favorite(name):
    """Retrieves a saved favorite by name if it exists"""
    favorites = config.get('Favorites')

    if name not in favorites:
        raise KeyError('No favorite for name \'%s\' exists' % name)

    favorite = favorites[name]
    return Favorite(name, favorite['Project'], favorite['Task'])


def add_favorite(name, project, task):
    """Saves a new favorite"""
    favorites = config.get('Favorites', {})

    if name in favorites:
        raise RuntimeError("Favorite '%s' already exists" % name)

    favorites[name] = {'Project': project, 'Task': task}
    config.set('Favorites', favorites)


def delete_favorite(name):
    """Delete a saved favorite if it exists"""
    favorites = config.get('Favorites', {})
    del favorites[name]
    config.set('Favorites', favorites)


class Favorite(dict):
    def __init__(self, name, project, task):
        self['Name'] = name
        self['Project'] = project
        self['Task'] = task

    def __getattr__(self, attr):
        return self[attr]
