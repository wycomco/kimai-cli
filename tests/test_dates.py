# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from kimai.dates import parse


class TestDates(object):

    def test_return_datetime_for_expression(self):
        date = parse('15 minutes ago')

        assert type(date) == datetime

    def test_create_date_relative_to_another_date(self):
        date = datetime(2018, 8, 5, 13, 15, 0)
        relative_date = parse('+15 minutes', date)
        delta = relative_date - date

        assert delta == timedelta(minutes=15)
