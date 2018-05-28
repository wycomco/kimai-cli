# -*- coding: utf-8 -*-

from kimai.cli import total_duration, print_total
from kimai.models import Record


class TestUtilityMethods(object):

    def test_total_of_no_records(self):
        assert '0:00h' == total_duration([])

    def test_total_of_a_single_record(self):
        record = Record('::record-id::', start='1527409161', duration='10800')
        actual = total_duration([record])
        assert '3:00h' == actual

    def test_total_of_multiple_records(self):
        record1 = Record(
            '::record-id::',
            start='1527409161',
            duration='10800'  # 3h
        )
        record2 = Record(
            '::record-id::',
            start='1527409161',
            duration='11700'  # 3h 15m
        )
        actual = total_duration([record1, record2])
        assert '6:15h' == actual

