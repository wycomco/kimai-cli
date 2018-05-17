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
    return KimaiResponse(_do_request(payload))


def stop_recording():
    """Stops the running record if there is one."""
    current_record = get_current()

    if current_record is None:
        return

    payload = _build_payload(
        'stopRecord',
        config.get('ApiKey'),
        current_record['timeEntryID']
    )
    return KimaiResponse(_do_request(payload))


def get_current():
    """Returns the currently running record if there is any."""
    timesheet = get_timesheet()

    if not timesheet:
        return

    if timesheet[0]['end'] != '0':
        return

    return timesheet[0]
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
    def __getitem__(self, key):
        if key in ['start', 'end']:
            value = int(super(Record, self).__getitem__(key))

            if value == 0:
                return '-'

            return datetime.fromtimestamp(value).strftime('%H:%M:%S')

        return super(Record, self).__getitem__(key)
