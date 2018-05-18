import requests
import json
import config
import dates
from datetime import datetime


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
    return requests.post('{}/core/json.php'.format(kimai_url), data=payload)


def authenticate(username, password):
    """Authenticate a user against the kimai backend."""
    payload = _build_payload('authenticate', username, password)
    response = _do_request(payload)
    return KimaiAuthResponse(response)


def get_projects():
    """Return a list of all available projects."""
    payload = _build_payload('getProjects', config.get('ApiKey'))
    response = KimaiResponse(_do_request(payload))
    return response.items


def get_tasks():
    """Return a list of all available tasks."""
    payload = _build_payload('getTasks', config.get('ApiKey'))
    response = KimaiResponse(_do_request(payload))
    return response.items


def start_recording(task_id, project_id):
    """Starts a new recording for the provided task and project."""
    payload = _build_payload(
        'startRecord',
        config.get('ApiKey'),
        project_id,
        task_id
    )

    response = KimaiResponse(_do_request(payload))

    if response.successful:
        current = get_current()
        config.set('CurrentEntry', current['timeEntryID'])

    return response


def stop_recording():
    """Stops the running record if there is one."""
    time_entry_id = config.get('CurrentEntry')

    if time_entry_id is None:
        current_record = get_current()
        time_entry_id = current_record['timeEntryID']

    payload = _build_payload(
        'stopRecord',
        config.get('ApiKey'),
        time_entry_id
    )

    response = KimaiResponse(_do_request(payload))

    if response.successful:
        config.delete('CurrentEntry')

    return response


def get_current():
    """Returns the currently running record if there is any."""
    timesheet = get_timesheet()

    if not timesheet:
        return

    if timesheet[0]['end'] != '0':
        return

    return Record(timesheet[0])


def get_todays_records():
    """Returns all records for the current day"""
    payload = _build_payload(
        'getTimesheet',
        config.get('ApiKey'),
        dates.parse('today at 00:00').isoformat(),
        dates.parse('today at 23:59:59').isoformat()
    )
    response = KimaiResponse(_do_request(payload))
    return [Record(r) for r in response.items]


def get_timesheet():
    payload = _build_payload('getTimesheet', config.get('ApiKey'))
    response = KimaiResponse(_do_request(payload))
    return response.items


def add_record(start, end, project, task, comment=''):
    payload = _build_record_payload('setTimesheetRecord', {
        'start': start.isoformat(),
        'end': end.isoformat(),
        'projectId': project,
        'taskId': task,
        'statusId': 1,
        'comment': comment
    })
    return KimaiResponse(_do_request(payload))


# TODO: Holy shit this doesn't check that I'm actually deleting one of my
#       own records...
def delete_record(id):
    payload = _build_payload('removeTimesheetRecord', config.get('ApiKey'), id)
    return KimaiResponse(_do_request(payload))


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
    def apiKey(self):
        if not self.successful:
            return None
        return self.items[0]['apiKey']


class Record(dict):
    """A single time tracking entry."""

    def __init__(self, seq, **kwargs):
        super().__init__(seq, **kwargs)

        self['start'] = datetime.fromtimestamp(int(self['start']))
        self['start_time'] = self['start'].strftime('%H:%M')

        if int(self['end']) == 0:
            self['end'] = None
            self['end_time'] = None
        else:
            self['end'] = datetime.fromtimestamp(int(self['end']))
            self['end_time'] = self['end'].strftime('%H:%M')

        self._calculate_duration()

    def _calculate_duration(self):
        if self['end'] is None:
            duration = (datetime.now() - self['start'])
        else:
            duration = (self['end'] - self['start'])

        self['timedelta'] = duration
        self['duration'] = ':'.join(str(duration).split(':')[:2])



