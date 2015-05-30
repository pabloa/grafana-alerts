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
        self.grafana_url = "http://localhost:3011/grafana/"
        self.grafana_token = "nabasiufbiqb3oibfo34bo34yb3ouqb"

    def read_config(self):
        pass

    def get_grafana_url(self):
        return self.grafana_url
