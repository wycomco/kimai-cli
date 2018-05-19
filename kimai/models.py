# -*- coding: utf-8 -*-

from datetime import datetime, timedelta


def create_record(data: dict):
    """Factory function to create a record from the raw Kimai JSON."""

    return Record(
        data['timeEntryID'],
        start=data['start'],
        end=data['end'],
        duration=data['duration'],
        formatted_duration=data.get('formattedDuration'),
        comment=data['comment'],
        customer=Customer(data['customerID'], data['customerName']),
        project=Project(data['projectID'], data['projectName']),
        task=Task(data['activityID'], data['activityName']),
        user_id=data['userID']
    )


class Project(object):
    def __init__(self, project_id, name):
        self.id = project_id
        self.name = name

    def __str__(self):
        return self.name


class Task(object):
    def __init__(self, task_id, name):
        self.id = task_id
        self.name = name

    def __str__(self):
        return self.name


class Customer(object):
    def __init__(self, customer_id, name):
        self.id = customer_id
        self.name = name

    def __str__(self):
        return self.name


class Favorite(object):
    def __init__(self, project, task):
        self.project = project
        self.task = task


class Record(object):
    """Represents a single entry in a time sheet."""

    def __init__(self, record_id, start=None, end=None, project=None, task=None,
                 customer=None, comment=None, duration=None, formatted_duration=None, user_id=None):
        # Convert timestamp strings to something more practical
        start = datetime.fromtimestamp(int(start))
        if end and end != '0':
            end = datetime.fromtimestamp(int(end))
        else:
            end = None

        # Convert duration to a timedelta so we can more easily add up running times
        if duration is not None:
            duration = timedelta(seconds=int(duration))

        # Kimai does not calculate a duration for a running record. So we do that ourselves.
        if not duration and not end:
            duration = datetime.now() - start

        self.id = record_id
        self.customer = customer
        self.task = task
        self.project = project
        self.end = end
        self.start = start
        self.comment = comment
        self.duration = duration
        self.formatted_duration = formatted_duration
        self.user_id = user_id
