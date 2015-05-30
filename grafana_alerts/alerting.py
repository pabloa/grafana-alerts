"""Alerts

"""
from multiprocessing.queues import JoinableQueue
import urllib2
import json

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = ["Pablo Alcaraz"]
__license__ = "Apache Software License V2.0"


class AlertCheckerCoordinator:
    """Entry point to the alert checking module."""

    def __init__(self, configuration):
        self.configuration = configuration
        self.queue = JoinableQueue()

    def check(self):
        """Check if there is something to report"""
        # Get all the dashboards to use for checking
        scanner = DashboardScanner(self.configuration.get_grafana_url(), self.configuration.get_grafana_token())
        dashboards = scanner.obtain_dashboards()
        print dashboards
        pass


class DashboardScanner:
    def __init__(self, grafana_url, grafana_token):
        self.grafana_url = grafana_url
        self.grafana_token = grafana_token

    def obtain_dashboards(self):
        request = urllib2.Request(self.grafana_url, headers={"Accept": "application/json",
                                                             "Authorization": "Bearer " + self.grafana_token})
        contents = urllib2.urlopen(request).read()
        data = json.load(contents)
        print data
