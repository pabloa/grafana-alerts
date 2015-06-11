from time import sleep

from grafana_alerts.alerting import DashboardScanner, Dashboard, AlertChecker
from grafana_alerts.reporting import ConsoleAlertReporter, MailAlertReporter
from tests.http_test_server import launch_webserver_in_new_thread, stop_webserver_in_new_thread

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = [""]
__license__ = "Apache Software License V2.0"

import unittest

grafana_url = "http://localhost:8000/grafana/"
grafana_token = "sfsdfsdf"
http_server_thread = None


class BaseAlertingTest(unittest.TestCase):
    def setUp(self):
        global http_server_thread
        if http_server_thread is None or not http_server_thread.isAlive():
            http_server_thread = launch_webserver_in_new_thread()
            sleep(1)

    def tearDown(self):
        sleep(1)
        stop_webserver_in_new_thread()


class DashboardScannerTest(BaseAlertingTest):
    def test_obtain_dashboards(self):
        # given
        scanner = DashboardScanner(grafana_url, grafana_token)
        self.assertIsNotNone(scanner)

        # when
        dashboards = scanner.obtain_dashboards()
        print dashboards

        # then
        self.assertIsNotNone(dashboards)
        self.assertEqual(5, len(dashboards))


class DashboardTest(BaseAlertingTest):
    def test_obtain_alert_checkers(self):
        # given
        title = 'TyProd Storage'
        slug = 'typrod-storage'
        tags = []
        console_alert_reporter = ConsoleAlertReporter()
        dashboard = Dashboard(grafana_url=grafana_url,
                              grafana_token=grafana_token, title=title, slug=slug, tags=tags)
        self.assertIsNotNone(dashboard)

        # when
        alert_checkers = dashboard.obtain_alert_checkers()
        print alert_checkers

        # then
        self.assertIsNotNone(alert_checkers)
        self.assertEqual(2, len(alert_checkers))


class AlertCheckerTest(BaseAlertingTest):
    def test_check_undefined_alert_criteria(self):
        # given
        title = 'TyProd Storage'
        grafana_targets = [{u'hide': False,
                            u'target': u"aliasByNode(exclude(typrod.*.disk_free_percent_rootfs.sum, '__SummaryInfo__'), 1)"}]
        alert_conditions = [
            ["50<=x<=100", "normal", "pablo@ailive.net"],
            ["35<x<50", "warning", "pablo@ailive.net"],
            ["x<=35", "critical", "pablo@ailive.net"]
        ]
        alert_checker = AlertChecker(grafana_url, grafana_token, title, grafana_targets)
        alert_checker.set_alert_conditions(alert_conditions=alert_conditions)
        self.assertIsNotNone(alert_checker)

        # when
        alert_checker.check()
        reported_alerts = alert_checker.get_reported_alerts()
        print reported_alerts

        # then
        self.assertIsNotNone(reported_alerts)
        self.assertEqual(7, len(reported_alerts))
        for reported_alert in reported_alerts:
            # check each reported alert meets an alert conditions status
            self.assertIsNotNone(reported_alert.current_alert_condition_status)
        return reported_alerts

    def test_alert_reporter(self):
        # given
        reported_alerts = self.test_check_undefined_alert_criteria()
        self.assertIsNotNone(reported_alerts)
        alert_reporter = MailAlertReportedWithMockedMailServer(email_from="builder@ailive.net", smtp_server="sendmail.ikuni.com", smtp_port=25)

        # when
        alert_reporter.report(reported_alerts)

        # then
        self.assertEqual(1, alert_reporter.get_sent_emails_counter())

class MailAlertReportedWithMockedMailServer(MailAlertReporter):
    def _send_email(self, email, email_to_string):
        self.sent_emails_counter+=1

# if __name__ == '__main__':
#     unittest.main()
