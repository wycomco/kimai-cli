# -*- coding: utf-8 -*-

import requests
import json

from functools import lru_cache

from . import dates, config
from .models import create_record


class RequestParameter(object):
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

        if self.quoted:
            return '\"%s\"' % value

        return value

    def __repr__(self):
        return self.build()


class RequestPayload(object):

    def __init__(self, action, requires_auth=True, params=None):
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


def _build_payload(method, *args):
    quoted_args = ['\"%s\"' % arg for arg in args]
    return '{"jsonrpc":"2.0", "method":"%s", "params":[%s], "id":"1"}' \
        % (method, ','.join(quoted_args))


def _do_request(payload):
    kimai_url = config.get('KimaiUrl')
    response = requests.post('{}/core/json.php'.format(kimai_url), data=payload)
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
    payload = RequestPayload(
        'getTimesheet',
        params=[
            RequestParameter(0),   # No particular start date
            RequestParameter(0),   # No particular end date
            RequestParameter(-1),  # Whatever this one is
            RequestParameter(0),   # No particular starting id
            RequestParameter(1)    # Limit to one record
        ]
    )
    user_records = _do_request(payload.build()).items

    if not user_records:
        raise RuntimeError('You are not authorized to edit this record')

    current_user_item = create_record(user_records[0])

    if not record.user_id == current_user_item.user_id:
        raise RuntimeError('You are not authorized to edit this record')


def authenticate(username, password):
    """Authenticate a user against the kimai backend."""

    payload = RequestPayload(
        'authenticate',
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

    return _do_request(RequestPayload('getProjects').build()).items


def get_tasks():
    """Return a list of all available tasks."""

    return _do_request(RequestPayload('getTasks').build()).items


def start_recording(task_id, project_id):
    """Starts a new recording for the provided task and project."""

    payload = RequestPayload(
        'startRecord',
        params=[
            RequestParameter(project_id),
            RequestParameter(task_id),
        ]
    )

    response = _do_request(payload.build())

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
        'stopRecord',
        params=[RequestParameter(time_entry_id)]
    )

    response = _do_request(payload.build())

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

    timesheet = get_timesheet()

    if not timesheet:
        return

    if timesheet[0]['end'] != '0':
        return

    return create_record(timesheet[0])


def get_todays_records():
    """Returns all records for the current day"""

    payload = RequestPayload(
        'getTimesheet',
        params=[
            RequestParameter(dates.parse('today at 00:00').isoformat()),
            RequestParameter(dates.parse('today at 23:59:59').isoformat()),
        ]
    )

    response = _do_request(payload.build())

    return [create_record(r) for r in response.items]


def get_timesheet():
    """Returns all time sheets for a user"""

    payload = RequestPayload('getTimesheet')
    response = _do_request(payload.build())

    return response.items


def get_single_record(record_id):
    """Retrieves a single record from Kimai"""

    payload = RequestPayload(
        'getTimesheetRecord',
        params=[RequestParameter(record_id)]
    )
    response = _do_request(payload.build())

    if response.successful:
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

    payload = RequestPayload('setTimesheetRecord', params=[record_param])

    return _do_request(payload.build())


def comment_on_record(record_id, comment):
    authorize_user(record_id)

    record = get_single_record(record_id)

    if not record:
        return

    payload = RequestPayload('setTimesheetRecord', params=[
        RequestParameter({
            'id': record.id,
            'start': record.start.isoformat(),
            'end': record.end.isoformat(),
            'projectId': record.project.id,
            'taskId': record.task.id,
            'statusId': 1,
            'comment': comment
        }, quoted=False),
        RequestParameter(True),  # Update the record
    ])

    response = _do_request(payload.build())


def delete_record(id):
    """Delete a record by its id. You can only delete your own records."""
    authorize_user(id)
    payload = _build_payload('removeTimesheetRecord', config.get('ApiKey'), id)
    return _do_request(payload)


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
