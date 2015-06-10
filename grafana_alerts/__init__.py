from grafana_alerts.launcher import Launcher


def main():
    """Entry point for the application script"""
    the_launcher = Launcher()
    return the_launcher.launch()
