"""Grafana Alert launcher.

"""
from grafana_alerts.alerting import AlertCheckerCoordinator

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = [""]
__license__ = "Apache Software License V2.0"


class Launcher:
    def launch(self):
        configuration = Configuration()
        alert_checker = AlertCheckerCoordinator(configuration)
        alert_checker.check()


class Configuration:
    """Store configuration."""

    def __init__(self):
        # TODO make sure the url finishes with '/' or requests could fail.
        self.grafana_url = 'http://localhost:3130/'
        self.grafana_token = ""
        self.email_from = "grafana-alert@localhost"
        self.smtp_server = "localhost"
        self.smtp_port = 25
        self.smtp_username = None
        self.smtp_password = None
        self.read_config()

    def read_config(self):
        try:
            with open("/etc/grafana_alerts/grafana_alerts.cfg", "r") as config_file:
                config = config_file.readlines()
                for line in config:
                    l = line.strip()
                    if len(l) == 0 or l.startswith('#'):
                        continue
                    k, v = [x.strip() for x in l.split('=', 1)]
                    setattr(self, k, v)
        except BaseException as e:
            raise RuntimeError("Error reading configuration /etc/grafana_alerts/grafana_alerts.cfg", e)
