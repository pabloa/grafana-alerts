from grafana_alerts.launcher import Launcher

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = [""]
__license__ = "Apache Software License V2.0"


def main():
    """Entry point for the application script"""
    the_launcher = Launcher()
    return the_launcher.launch()
