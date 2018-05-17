from datetime import datetime
import parsedatetime


def parse(expression, relative_date=None):
    cal = parsedatetime.Calendar()
    struct, status = cal.parse(expression, relative_date)
    return datetime(*struct[:6]) # I know, right?
