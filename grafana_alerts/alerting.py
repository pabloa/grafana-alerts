"""Alerts

"""
from multiprocessing.queues import JoinableQueue
import urllib2
import json

import jmespath
from grafana_alerts.reporting import AlertReporter

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = ["Pablo Alcaraz"]
__license__ = "Apache Software License V2.0"

_GRAFANA_URL_PATH_OBTAIN_DASHBOARDS = '/api/search?limit=10&query=&tag='
_GRAFANA_URL_PATH_DASHBOARD = '/api/dashboards/db/{slug}'


class AlertCheckerCoordinator:
    """Entry point to the alert checking module."""

    def __init__(self, configuration):
        self.configuration = configuration
        self.queue = JoinableQueue()

    def check(self):
        """Check if there is something to report"""
        # Get all the dashboards to use for checking
        self.alert_reporter = AlertReporter()
        scanner = DashboardScanner(self.configuration.get_grafana_url(), self.configuration.get_grafana_token())
        dashboard_data_list = scanner.obtain_dashboards()
        print dashboard_data_list
        for d in dashboard_data_list:
            # {u'slug': u'typrod-storage', u'tags': [], u'isStarred': False, u'id': 4, u'title': u'TyProd Storage'}
            dashboard = Dashboard(d.title, d.slug, d.tags)
            alert_list = dashboard.obtain_alert_checkers()
            print alert_list


class AlertChecker:
    """Command to check metrics."""

    def __init__(self, title, grafana_targets):
        self.title = title
        self.grafana_targets = grafana_targets

    def set_alert_conditions(self, alert_conditions):
        self.alert_conditions = alert_conditions

    def check(self):
        pass

    def get_reported_alerts(self):
        return []


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
    def __init__(self, alert_reporter, grafana_url, grafana_token, title, slug, tags):
        self.alert_reporter = alert_reporter
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
        print contents
        data = json.loads(contents)
        dashboard = jmespath.search('model.rows[*].panels[*]', data)
        return dashboard

    def _create_alert_checkers(self, dashboard_info):
        """check metrics and return a list of alerts to evaluate."""
        for dashboard_row in dashboard_info:
            print dashboard_row
            # creates alert checkers from the row.
            # TODO add alert checker creation to a builder dashboard_row2alert_checker_list.
            alert_conditions = []  # map of alert conditions( text -> alert parameters)
            alert_checkers = []
            for row in dashboard_row:
                print row
                print row['type']
                if row['type'] == "graph":
                    # print row['leftYAxisLabel']
                    # print row['y_formats']
                    alert_checker = AlertChecker(row['title'], row['targets'])
                    alert_checkers.append(alert_checker)
                elif row['type'] == "singlestat":
                    alert_checker = AlertChecker(row['title'], row['targets'])
                    # print row['thresholds']
                    alert_checkers.append(alert_checker)
                elif row['type'] == "text":
                    if row['title'] == 'alerts':
                        # read alert parameters to apply to all the alert checkers of this row.
                        for line in row['content'].splitlines():
                            # TODO replace alert_definition_list for an object
                            alert_definition_list = line.split(',')
                            if len(alert_definition_list) > 1:
                                alert_conditions.append(alert_definition_list)
                else:
                    print "Unknown type {type}. Ignoring.".format(type=row['type'])

            if len(alert_conditions) > 0:
                # There are alert conditions, add them to all the alert_checkers.
                for alert_checker in alert_checkers:
                    alert_checker.set_alert_conditions(alert_conditions)
        return alert_checkers
