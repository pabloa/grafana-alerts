__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = ["Pablo Alcaraz"]
__license__ = "Apache Software License V2.0"

_GRAFANA_URL_PATH_OBTAIN_DASHBOARDS = '/api/search?limit=10&query=&tag='
_GRAFANA_URL_PATH_DASHBOARD = '/api/dashboards/db/{slug}'


class BaseAlertReporter:
    def report(self, bla):
        raise NotImplemented("Implement me")


class AlertReporter(BaseAlertReporter):
    pass


class ConsoleAlertReporter(BaseAlertReporter):
    pass
