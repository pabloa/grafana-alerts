__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = ["Pablo Alcaraz"]
__license__ = "Apache Software License V2.0"

_GRAFANA_URL_PATH_OBTAIN_DASHBOARDS = '/api/search?limit=10&query=&tag='
_GRAFANA_URL_PATH_DASHBOARD = '/api/dashboards/db/{slug}'


class AlertEvaluationResult:
    """Alert evaluation information. All the information needed to decide if an email will be sent and the information
    to send should be here."""
    def __init__(self, title, target):
        self.title = title
        self.target = target
        self.alert_conditions = {}
        self.current_alert_condition_status = None
        self.value = None

    def set_current_value(self, value):
        self.value = value

    def add_alert_condition_result(self, name, condition, activated, alert_destination, title):
        alert_condition_status = {
            'name': name,
            'condition': condition,
            'activated': activated,
            'alert_destination': alert_destination,
            'title': title
        }
        # alert_condition_status = {
        #     'name': alert_condition[1],
        #     'condition': condition,
        #     'activated': activated,
        #     'alert_destination': alert_condition[2],
        #     'title': self.title
        # }
        self.alert_conditions[name] = alert_condition_status
        if alert_condition_status['activated']:
            # point to the activated alert condition status.
            self.current_alert_condition_status = alert_condition_status

class BaseAlertReporter:
    def report(self, bla):
        raise NotImplemented("Implement me")


class AlertReporter(BaseAlertReporter):
    pass


class ConsoleAlertReporter(BaseAlertReporter):
    pass
