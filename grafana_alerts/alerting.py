"""Alerts

"""
from multiprocessing.queues import JoinableQueue
import urllib2
import json

import jmespath

from grafana_alerts.reporting import AlertEvaluationResult, MailAlertReporter

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = [""]
__license__ = "Apache Software License V2.0"

_GRAFANA_URL_PATH_OBTAIN_DASHBOARDS = 'api/search?limit=10&query=&tag=monitored'
_GRAFANA_URL_PATH_DASHBOARD = 'api/dashboards/db/{slug}'
_GRAFANA_URL_PATH_OBTAIN_METRICS = 'api/datasources/proxy/1/render'


class NotMonitoreableDashboard(RuntimeError):
    def __init__(self, message):
        self.message = message

class AlertCheckerCoordinator:
    """Entry point to the alert checking module."""

    def __init__(self, configuration):
        self.configuration = configuration
        self.queue = JoinableQueue()
        self.alert_reporter = MailAlertReporter(email_from=self.configuration.email_from, smtp_server=self.configuration.smtp_server, smtp_port=self.configuration.smtp_port, email_username=self.configuration.smtp_username, email_password=self.configuration.smtp_password)

    def check(self):
        """Check if there is something to report"""
        # Get all the dashboards to use for checking
        scanner = DashboardScanner(self.configuration.grafana_url, self.configuration.grafana_token)
        dashboard_data_list = scanner.obtain_dashboards()
        print dashboard_data_list
        for d in dashboard_data_list:
            try:
                print "Dashboard: " + d['title']
                # {u'slug': u'typrod-storage', u'tags': [], u'isStarred': False, u'id': 4, u'title': u'TyProd Storage'}
                dashboard = Dashboard(self.configuration.grafana_url, self.configuration.grafana_token, d['title'], d['slug'], d['tags'])
                alert_checkers = dashboard.obtain_alert_checkers()
                print alert_checkers

                # For each set of alert checkers, evaluate them
                for alert_checker in alert_checkers:
                    alert_checker.check()
                    reported_alerts = alert_checker.get_reported_alerts()
                    # for each set of reported alerts, report whatever is best
                    self.alert_reporter.report(reported_alerts)
            except NotMonitoreableDashboard as e:
                print "Dashboard {title} cannot be monitored. Reason: {reason}".format(title = d['title'], reason=e.message)
                continue


class AlertChecker:
    """Command to check metrics."""

    def __init__(self, grafana_url, grafana_token, title, grafana_targets):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token
        self.title = title
        self.grafana_targets = grafana_targets
        self.checkedExecuted = False
        self.responses = []
        self.alert_conditions = None

    def set_alert_conditions(self, alert_conditions):
        """Alerts conditions are composed by an array of elements.
        each element is an array like:

            [["interval1","status1","alert destination1","short description","long description"],
            ["interval2","status2","alert destination2","short description","long description"],
            ["intervaln","statusN","alert destinationN","short description","long description"]]

        interval: string representing an interval like:
            "x<=0": -infinite < x <= 0
            "0<=x<50": [0;50)
            "50<=x": 50 <= x < infinite

        status: "normal", "warning", "critical"

        alert destination: 1 or more emails separated by ","

        example:
            [["50<=x<=100", "normal", "p@q.com"],
            ["50<x<=35", "warning", "p@q.com"],
            ["35<=x", "critical", "p@q.com"]]
        """
        # TODO verify alert conditions are valid.
        self.alert_conditions = alert_conditions

    def check(self):
        """get metrics from grafana server"""
        for grafana_target in self.grafana_targets:
            if not grafana_target['hide']:
                target = grafana_target['target']
                post_parameters = "target={target}&from=-60s&until=now&format=json&maxDataPoints=100".format(
                    target=target)
                request = urllib2.Request(self.grafana_url + _GRAFANA_URL_PATH_OBTAIN_METRICS,
                                          data=post_parameters,
                                          headers={"Accept": "application/json",
                                                   "Authorization": "Bearer " + self.grafana_token})

                contents = urllib2.urlopen(request).read()
                self.responses.append(json.loads(contents))
        self.checkedExecuted = True

    def get_reported_alerts(self):
        alert_evaluation_result_list = []
        if not self.checkedExecuted:
            raise RuntimeError("method check() was not invoked, therefore there is nothing to report about. Fix it.")

        if self.alert_conditions is None:
            raise RuntimeError(
                "method set_alert_conditions() was not invoked, therefore there is nothing to report about. Fix it.")

        for response in self.responses:
            # A grafana response could cover several sources/hosts.
            for source in response:
                alert_evaluation_result = AlertEvaluationResult(title=self.title, target=source['target'])
                # for now 'x' is the average of all not null data points.
                data = [m[0] for m in source['datapoints'] if m[0] is not None]
                if len(data) > 0:
                    x = float(sum(data)) / len(data)
                else:
                    x = float('nan')
                alert_evaluation_result.set_current_value(x)

                # evaluate all the alert conditions and create a current alert status.
                for alert_condition in self.alert_conditions:
                    condition = alert_condition[0]
                    activated = eval(condition)
                    alert_evaluation_result.add_alert_condition_result(name=alert_condition[1], condition=condition,
                                                                       activated=activated,
                                                                       alert_destination=alert_condition[2],
                                                                       title=self.title)

                alert_evaluation_result_list.append(alert_evaluation_result)

        return alert_evaluation_result_list


class DashboardScanner:
    def __init__(self, grafana_url, grafana_token):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token

    def obtain_dashboards(self):
        request = urllib2.Request(self.grafana_url + _GRAFANA_URL_PATH_OBTAIN_DASHBOARDS,
                                  headers={"Accept": "application/json",
                                           "Authorization": "Bearer " + self.grafana_token})
        contents = urllib2.urlopen(request).read()
        print contents
        data = json.loads(contents)
        dashboards = jmespath.search('dashboards', data)
        return dashboards


class Dashboard:
    def __init__(self, grafana_url, grafana_token, title, slug, tags):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token
        self.title = title
        self.slug = slug
        self.tags = tags

    def obtain_alert_checkers(self):
        """check metrics and return a list of triggered alerts."""
        dashboard_info = self._obtain_dashboard_rows()
        alert_checkers = self._create_alert_checkers(dashboard_info)
        return alert_checkers

    def _obtain_dashboard_rows(self):
        """Get a list of dashboard rows."""
        request = urllib2.Request(self.grafana_url + _GRAFANA_URL_PATH_DASHBOARD.format(slug=self.slug),
                                  headers={"Accept": "application/json",
                                           "Authorization": "Bearer " + self.grafana_token})
        contents = urllib2.urlopen(request).read()
        # Fix \n inside json values.
        contents = contents.replace('\r\n', '\\r\\n').replace('\n', '\\n')
        print "Contents is: "
        print contents
        try:
            data = json.loads(contents)
            dashboard = jmespath.search('model.rows[*].panels[*]', data)
            return dashboard
        except ValueError:
            raise NotMonitoreableDashboard( "The definition of dashboard {title} does not look like valid json.".format(title=self.title))

    def _create_alert_checkers(self, dashboard_info):
        """check metrics and return a list of alerts to evaluate."""
        alert_checkers = []
        for dashboard_row in dashboard_info:
            print dashboard_row
            # creates alert checkers from the row.
            # TODO add alert checker creation to a builder dashboard_row2alert_checker_list.
            alert_conditions = []  # map of alert conditions( text -> alert parameters)
            for row in dashboard_row:
                print row
                print row['type']
                if row['type'] == "graph":
                    # print row['leftYAxisLabel']
                    # print row['y_formats']
                    alert_checker = AlertChecker(self.grafana_url, self.grafana_token, row['title'], row['targets'])
                    alert_checkers.append(alert_checker)
                elif row['type'] == "singlestat":
                    alert_checker = AlertChecker(self.grafana_url, self.grafana_token, row['title'], row['targets'])
                    # print row['thresholds']
                    alert_checkers.append(alert_checker)
                elif row['type'] == "text":
                    if row['title'] == 'alerts':
                        # read alert parameters to apply to all the alert checkers of this row.
                        for line in row['content'].splitlines():
                            # TODO replace alert_definition_list for an object
                            alert_definition_list = [ s.strip() for s in line.split(';')]
                            if len(alert_definition_list) > 1:
                                alert_conditions.append(alert_definition_list)
                else:
                    print "Unknown type {type}. Ignoring.".format(type=row['type'])

            if len(alert_conditions) > 0:
                # There are alert conditions, add them to all the alert_checkers.
                for alert_checker in alert_checkers:
                    alert_checker.set_alert_conditions(alert_conditions)
        return alert_checkers
