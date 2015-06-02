from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import smtplib
import datetime

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
    def report(self, reported_alert):
        raise NotImplemented("Implement me")


class MailAlertReporter(BaseAlertReporter):
    def __init__(self, email_from, smtp_server, smtp_port, email_username=None, email_password=None):
        self.email_from = email_from
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_username = email_username
        self.email_password = email_password
        self.sent_emails_counter = 0

    def report(self, reported_alerts):
        filtered_reported_alert = self._filter(reported_alerts=reported_alerts)
        # TODO keys should have better names.
        alerts_to_send_map = self._consolidate(filtered_reported_alert, 'alert_destination')
        self._send(alerts_to_send_map)

    def _filter(self, reported_alerts):
        # TODO filter by not normal
        # TODO later filter by: if there is not persisted previous state ? not normal : state changed.
        return reported_alerts;

    def _consolidate(self, filtered_reported_alerts, group_by):
        """Given reported alerts evaluation results. Consolidates them by the given key.
        For example: 1 mail with a list of alerts groups by destination, etc.
        :return a map, the key is the field 'group_by', the value is a list of alert evaluation results.
        """
        consolidated_map = {}

        for alert_evaluation_result in filtered_reported_alerts:
            try:
                key = eval("alert_evaluation_result." + group_by)
            except AttributeError:
                key = eval(
                    "alert_evaluation_result.current_alert_condition_status['{group_by}']".format(group_by=group_by))
            if not consolidated_map.has_key(key):
                consolidated_map[key] = []
            consolidated_map[key].append(alert_evaluation_result)
        return consolidated_map

    def _send(self, alerts_to_send_map):
        """Send the alerts.
        This version only supports grouping by email."""
        for email_to_string, alert_evaluation_result_list in alerts_to_send_map.iteritems():
            html_version_main = self._html_version_main()
            html_version_items = self._html_version_items(alert_evaluation_result_list)
            html_version = html_version_main.format(html_version_items=html_version_items,
                                                    # TODO Externalize variables
                                                    date=datetime.datetime.now().strftime("%B %d, %Y"),
                                                    time=datetime.datetime.now().strftime("%I:%M %p"),
                                                    message_signature=hashlib.sha256(html_version_main + html_version_items + datetime.datetime.now().strftime("%B %d, %Y - %I:%M %p")).hexdigest(),
                                                    companyName=""
                                                    )
            # text_version = bs.get_text()

            # create email
            email = MIMEMultipart('alternative')
            # TODO calculate this value.
            email['Subject'] = "monitoring alert"
            email['From'] = self.email_from
            # email_to = email_to_string.split(',')
            email['To'] = email_to_string
            # part_text = MIMEText(text_version, 'plain', 'utf-8')
            # email.attach(part_text)
            part_html = MIMEText(html_version, 'html', 'utf-8')
            email.attach(part_html)

            # send mail
            mail_server = smtplib.SMTP(host=self.smtp_server, port=self.smtp_port)
            if self.email_username is not None:
                mail_server.login(self.email_username, self.email_password)
            try:
                mail_server.sendmail(self.email_from, email_to_string, email.as_string())
                self.sent_emails_counter += 1
            finally:
                mail_server.close()

    def _html_version_items(self, alert_evaluation_result_list):
        html = ''
        for alert_evaluation_result in alert_evaluation_result_list:
            variables = alert_evaluation_result.current_alert_condition_status.copy()
            variables['target'] = alert_evaluation_result.target
            variables['value'] = alert_evaluation_result.value
            variables['alertName'] = alert_evaluation_result.current_alert_condition_status['name']
            # variables['date'] = datetime.datetime.now().strftime("%B %d, %Y"),
            # variables['time'] = datetime.datetime.now().strftime("%I:%M %p"),
            html_item = self._html_version_item().format(**variables)
            html += html_item
        return html

    def _html_version_item(self):
        """html version of the list of alert_evaluation_result_list."""
        with open("data/html_version_item.html", "r") as main_item_file:
            main_item = main_item_file.read()
            return main_item

    def _html_version_main(self):
        """html version of the email. It must returns everything except "html_version_items"""
        with open("data/html_version_main.html", "r") as main_text_file:
            main_text = main_text_file.read()
            return main_text

    def get_sent_emails_counter(self):
        return self.sent_emails_counter


class ConsoleAlertReporter:
    pass
