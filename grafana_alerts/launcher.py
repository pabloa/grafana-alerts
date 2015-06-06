"""Grafana Alert launcher.

"""
from grafana_alerts.alerting import AlertCheckerCoordinator

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = ["Pablo Alcaraz"]
__license__ = "Apache Software License V2.0"


class Launcher:
    def launch(self):
        configuration = Configuration()
        configuration.read_config()
        alert_checker = AlertCheckerCoordinator(configuration)
        alert_checker.check()


class Configuration:
    """Store configuration."""

    def __init__(self):
        # TODO make sure the url finishes with '/' or requests could fail.
        # self.grafana_url = "http://localhost:3011/grafana/"
        self.grafana_url = "http://localhost:8000/grafana/"
        self.grafana_token = "nabasiufbiqb3oibfo34bo34yb3ouqb"
        self.email_from = "builder@ailive.net"
        self.smtp_server = "sendmail.ikuni.com"
        self.smtp_port = 25

    def read_config(self):
        # TODO Implement me
        pass

