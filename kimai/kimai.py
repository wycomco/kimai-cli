# -*- coding: utf-8 -*-

import requests
import json

from functools import lru_cache

from . import dates, config
from .models import create_record


def _build_payload(method, *args):
    quoted_args = ['\"%s\"' % arg for arg in args]
    return '{"jsonrpc":"2.0", "method":"%s", "params":[%s], "id":"1"}' \
        % (method, ','.join(quoted_args))


def _build_record_payload(method, record, update=False):
    # Make it compatible with PHP's json decode
    update = 'true' if update else 'false'

    return '{"jsonrpc":"2.0", "method":"%s", "params":["%s", %s, %s], "id":"1"}' \
        % (method, config.get('ApiKey'), json.dumps(record), update)


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
    payload = _build_payload(
        'getTimesheet',
        config.get('ApiKey'),
        0,   # No particular start date
        0,   # No particular end date
        -1,  # Whatever this one is
        0,   # No particular starting id
        1    # Limit to one record
    )
    user_records = _do_request(payload).items

    if not user_records:
        raise RuntimeError('You are not authorized to edit this record')

    current_user_item = create_record(user_records[0])

    if not record.user_id == current_user_item.user_id:
        raise RuntimeError('You are not authorized to edit this record')


def authenticate(username, password):
    """Authenticate a user against the kimai backend."""

    payload = _build_payload('authenticate', username, password)
    response = requests.post('{}/core/json.php'.format(config.get('KimaiUrl')), data=payload)

    return KimaiAuthResponse(response)


def get_projects():
    """Return a list of all available projects."""

    payload = _build_payload('getProjects', config.get('ApiKey'))

    return _do_request(payload).items


def get_tasks():
    """Return a list of all available tasks."""

    payload = _build_payload('getTasks', config.get('ApiKey'))

    return _do_request(payload).items


def start_recording(task_id, project_id):
    """Starts a new recording for the provided task and project."""

    payload = _build_payload(
        'startRecord',
        config.get('ApiKey'),
        project_id,
        task_id
    )

    response = _do_request(payload)

    if response.successful:
        current = get_current()
        config.set('CurrentEntry', current['timeEntryID'])

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
        time_entry_id = current_record['timeEntryID']

    payload = _build_payload(
        'stopRecord',
        config.get('ApiKey'),
        time_entry_id
    )

    response = _do_request(payload)

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

    payload = _build_payload(
        'getTimesheet',
        config.get('ApiKey'),
        dates.parse('today at 00:00').isoformat(),
        dates.parse('today at 23:59:59').isoformat()
    )

    response = _do_request(payload)

    return [create_record(r) for r in response.items]


def get_timesheet():
    """Returns all time sheets for a user"""

    payload = _build_payload('getTimesheet', config.get('ApiKey'))
    response = _do_request(payload)
    return response.items


def get_single_record(record_id):
    """Retrieves a single record from Kimai"""

    payload = _build_payload('getTimesheetRecord', config.get('ApiKey'), record_id)
    response = _do_request(payload)

    if response.successful:
        return create_record(response.items[0])


def add_record(start, end, project, task, comment=''):
    """Add a new record to Kimai"""
    payload = _build_record_payload('setTimesheetRecord', {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'projectId': project,
        'taskId': task,
        'statusId': 1,
        'comment': comment
    })
    return _do_request(payload)


def comment_on_record(record_id, comment):
    authorize_user(record_id)

    record = get_single_record(record_id)

    if not record:
        return

    record.comment = comment

    payload = _build_record_payload('setTimesheetRecord', {
        'id': record.timeEntryID,
        'start': record.start.isoformat(),
        'end': record.end.isoformat(),
        'projectId': record.projectID,
        'taskId': record.activityID,
        'statusId': 1,
        'comment': comment
    }, update=True)

    response = _do_request(payload)


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
