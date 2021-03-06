# -*- coding: utf-8 -*-

import requests
import json

from enum import Enum
from typing import List
from functools import lru_cache

from . import dates
from .config import config
from .models import create_record


class RequestAction(Enum):
    """Represents one of the possible api services the Kimai API supports."""

    AUTHENTICATE = 'authenticate'
    GET_PROJECTS = 'getProjects'
    GET_TASKS = 'getTasks'
    START_RECORD = 'startRecord'
    STOP_RECORD = 'stopRecord'
    GET_TIMESHEET = 'getTimesheet'
    GET_TIMESHEET_RECORD = 'getTimesheetRecord'
    SET_TIMESHEET_RECORD = 'setTimesheetRecord'
    REMOVE_TIMESHEET_RECORD = 'removeTimesheetRecord'

    def __str__(self):
        return self._value_


class RequestParameter(object):
    """Represents a single parameter that gets sent as part of the request
    payload."""

    def __init__(self, value, quoted=True):
        self.quoted = quoted
        self.value = value

    def build(self):
        value = self.value

        if type(self.value) == bool:
            # Convert a python boolean into something the Kimai API can process
            value = 'false' if not value else 'true'
        elif type(self.value) == dict:
            value = json.dumps(self.value)

        # Some parameters need to be quoted, others don't...
        if self.quoted:
            return '\"%s\"' % value

        return value

    def __repr__(self):
        return self.build()


class RequestPayload(object):
    """Represents the string that gets send as the request payload."""

    def __init__(self, action: RequestAction, requires_auth=True, params: List[RequestParameter]=None):
        self.action = action
        self.api_key = None if not requires_auth else config.get('ApiKey')
        self.params = [] if not params else params

    def build(self):
        params = [p.build() for p in self.params]

        # Prepend api key to parameters if it exists
        if self.api_key:
            params = ['"%s"' % self.api_key] + params

        return '{"jsonrpc":"2.0", "method": "%s", "params": [%s], "id": 1}' \
               % (self.action, ','.join(params))

    def __repr__(self):
        return self.build()


def send_request(payload: RequestPayload):
    """Sends the request described in the payload to the Kimai API."""

    kimai_url = config.get('KimaiUrl')
    response = requests.post('{}/core/json.php'.format(kimai_url), data=payload.build())

    return KimaiResponse(response)


@lru_cache()
def authorize_user(record_id):
    record = get_single_record(record_id)

    if not record:
        raise RuntimeError('No record exists for id %s' % record_id)

    # This is hack around the fact that the Kimai API does not check whether or not
    # the current user actually has permissions to edit a record. Since there is no
    # direct way of retrieving the current user's id, we have to help ourselves by
    # simply retrieving any record using the saved API key and compare the returned
    # record's user id with the user id of the record we're trying to operate on.
    user_records = get_timesheet(limit=1)

    if not user_records:
        raise RuntimeError('You are not authorized to edit this record')

    current_user_item = user_records[0]

    if not record.user_id == current_user_item.user_id:
        raise RuntimeError('You are not authorized to edit this record')


def authenticate(username, password):
    """Authenticate a user against the kimai backend."""

    payload = RequestPayload(
        RequestAction.AUTHENTICATE,
        requires_auth=False,
        params=[
            RequestParameter(username),
            RequestParameter(password),
        ]
    )
    response = requests.post('{}/core/json.php'.format(config.get('KimaiUrl')), data=payload.build())

    return KimaiAuthResponse(response)


def get_projects():
    """Return a list of all available projects."""
    return send_request(
        RequestPayload(RequestAction.GET_PROJECTS)
    ).items


def get_tasks():
    """Return a list of all available tasks."""
    return send_request(
        RequestPayload(RequestAction.GET_TASKS)
    ).items


def start_recording(task_id, project_id):
    """Starts a new recording for the provided task and project."""

    payload = RequestPayload(
        RequestAction.START_RECORD,
        params=[
            RequestParameter(project_id),
            RequestParameter(task_id),
        ]
    )

    response = send_request(payload)

    if response.successful:
        current = get_current()
        config.set('CurrentEntry', current.id)

    return response


def stop_recording():
    """Stops the running record if there is one."""

    time_entry_id = config.get('CurrentEntry')

    if time_entry_id is not None:
        # Since the saved time entry id could have been tampered with by someone
        # editing the config directly, we have to check it again here.
        authorize_user(time_entry_id)
    else:
        current_record = get_current()
        time_entry_id = current_record.id

    payload = RequestPayload(
        RequestAction.STOP_RECORD,
        params=[RequestParameter(time_entry_id)]
    )

    response = send_request(payload)

    # If we were successful in stopping the running record we now try to set
    # its comment if the user entered one. We have to do it like this because
    # Kimai does not expose a direct way to edit a running record.
    if response.successful:
        comment = config.get('Comment')

        if comment:
            comment_on_record(time_entry_id, comment)
            # Make sure we delete the comment if we successfully saved it.
            # Otherwise it would show up for the next record as well.
            config.delete('Comment')

        config.delete('CurrentEntry')

    return response


def get_current():
    """Returns the currently running record if there is any."""

    timesheet = get_timesheet(limit=1)
    if not timesheet:
        return

    record = timesheet[0]

    if record.end:
        return

    return record


def get_todays_records():
    """Returns all records for the current day"""
    return get_timesheet(
        dates.parse('today at 00:00').isoformat(),
        dates.parse('today at 23:59:59').isoformat()
    )


def get_timesheet(start_date=0, end_date=0, limit=0):
    """Returns all time sheets for a user"""

    payload = RequestPayload(
        RequestAction.GET_TIMESHEET,
        params=[
            RequestParameter(start_date),  # Time of first entry to fetch
            RequestParameter(end_date),    # Time of last entry to fetch
            RequestParameter(-1),          # Whatever this one is
            RequestParameter(0),           # No particular starting id
            RequestParameter(limit)        # How many records to fetch
        ]
    )
    response = send_request(payload)

    return [create_record(r) for r in response.items]


def get_single_record(record_id):
    """Retrieves a single record from Kimai"""

    payload = RequestPayload(
        RequestAction.GET_TIMESHEET_RECORD,
        params=[RequestParameter(record_id)]
    )
    response = send_request(payload)

    if not response.successful:
        raise KeyError('No record exists for id %s' % record_id)

    return create_record(response.items[0])


def add_record(start, end, project, task, comment=''):
    """Add a new record to Kimai"""

    record_param = RequestParameter({
        'start': start.isoformat(),
        'end': end.isoformat(),
        'projectId': project,
        'taskId': task,
        'statusId': 1,
        'comment': comment
    }, quoted=False)

    payload = RequestPayload(RequestAction.SET_TIMESHEET_RECORD, params=[record_param])

    return send_request(payload)


def edit_record(record_id, start=None, end=None, comment=None, project_id=None, task_id=None):
    authorize_user(record_id)

    record = get_single_record(record_id)

    if not record:
        raise KeyError('No entry exists for id %s' % record_id)

    start = record.start if start is None else start
    end = record.end if end is None else end
    comment = record.comment if comment is None else comment
    project_id = record.project.id if project_id is None else project_id
    task_id = record.task.id if task_id is None else task_id

    record_param = RequestParameter({
        'id': record_id,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'projectId': project_id,
        'taskId': task_id,
        'statusId': 1,
        'comment': comment
    }, quoted=False)

    payload = RequestPayload(
        RequestAction.SET_TIMESHEET_RECORD,
        params=[
            record_param,
            RequestParameter(True)  # Update the record
        ]
    )

    return send_request(payload)


def comment_on_record(record_id, comment):
    return edit_record(record_id, comment=comment)


def delete_record(id):
    """Delete a record by its id. You can only delete your own records."""
    authorize_user(id)
    payload = RequestPayload(RequestAction.REMOVE_TIMESHEET_RECORD, params=[RequestParameter(id)])
    return send_request(payload)


class KimaiResponse(object):
    """Generic response object for the Kimai (sort of) JSON API"""

    def __init__(self, response):
        self.data = json.loads(response.text)['result']

    @property
    def successful(self):
        return self.data['success']

    @property
    def error(self):
        if self.successful:
            return None
        return self.data['error']['msg']

    @property
    def items(self):
        if not self.successful:
            return None
        return self.data['items']


class KimaiAuthResponse(KimaiResponse):
    """Specific response for the result of an authentication request"""

    @property
    def api_key(self):
        if not self.successful:
            return None
        return self.items[0]['apiKey']
