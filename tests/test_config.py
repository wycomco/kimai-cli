# -*- coding: utf-8 -*-

from kimai.config import Config


class TestConfig(object):

    def test_getting_an_existing_value(self):
        config = Config({'::existing-key::': '::value::'})

        result = config.get('::existing-key::')

        assert '::value::' == result

    def test_getting_a_none_existing_value(self):
        config = Config()

        result = config.get('::non-existing-key::')

        assert result is None

    def test_getting_default_value_for_non_existent_key(self):
        config = Config()

        result = config.get('::non-existing-key::', '::default::')

        assert '::default::' == result

    def test_default_getting_ignored_if_value_exists(self):
        config = Config({'::key::': '::value::'})

        result = config.get('::key::', '::default::')

        assert '::value::' == result

    def test_setting_a_value_that_didnt_exist(self):
        config = Config()

        config.set('::key::', '::value::')

        result = config.get('::key::')
        assert '::value::' == result

    def test_overriding_an_existing_value(self):
        config = Config({'::key::': '::old-value::'})

        config.set('::key::', '::new-value::')

        result = config.get('::key::')
        assert '::new-value::' == result

    def test_deleting_a_value(self):
        config = Config({'::key::': '::value::'})

        config.delete('::key::')

        result = config.get('::key::')
        assert result is None
