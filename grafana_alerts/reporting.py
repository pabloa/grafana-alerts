from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import os
import pickle
import smtplib
import datetime
import pkg_resources

__author__ = 'Pablo Alcaraz'
__copyright__ = "Copyright 2015, Pablo Alcaraz"
# __credits__ = [""]
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
        # TODO remove
        self.sent_emails_counter = 0

    def report(self, reported_alerts):
        filtered_reported_alert = self._filter(reported_alerts=reported_alerts)
        diff_report = self._generated_diff_report(filtered_reported_alert)
        # TODO keys should have better names.
        alerts_to_send_map = self._group_by(diff_report, 'alert_destination')
        self._send_alerts_if_any(alerts_to_send_map)

    def _filter(self, reported_alerts):
        # TODO Add filtering capabilites
        return reported_alerts

    def _generated_diff_report(self, reported_alerts):
        GRAFANA_MONITOR_STATE = '/tmp/grafana_monitor.state'
        # read last state
        old_alerts_state = {}
        if os.path.isfile(GRAFANA_MONITOR_STATE):
            with open(GRAFANA_MONITOR_STATE, 'r') as f:
                old_alerts_state = pickle.load(f)

        # collect current state
        current_alerts_state = {}
        for aer in reported_alerts:
            if aer.current_alert_condition_status is None:
                # TODO This happens because we are not getting stats from grafana, perhaps server was reainstalled without monitoring tools?
                # TODO generate a warning or something according to config definition.
                aer_current_alert_condition_status_name = "None"
            else:
                aer_current_alert_condition_status_name = aer.current_alert_condition_status['name']
            key = "{target}, {title}, {alert_name}".format(target=aer.target, title=aer.title, alert_name=aer_current_alert_condition_status_name)
            # value = "{condition},{activated}".format(condition=aer.current_alert_condition_status['condition'], activated=aer.current_alert_condition_status['activated'])
            value = aer
            current_alerts_state[key] = value

        # persist new state
        with open(GRAFANA_MONITOR_STATE, 'w') as f:
            pickle.dump(current_alerts_state, f)

        # compare old with new state and generates report with 4 causes of diff: changed, lost, new, unchanged.
        diff_report = []
        for current_key, current_value in current_alerts_state.iteritems():
            current_element = current_value
            old_element = None
            diff = 'new'
            if old_alerts_state.has_key(current_key):
                old_value = old_alerts_state[current_key]
                old_element = old_value
                if old_value.current_alert_condition_status is None and current_value.current_alert_condition_status is None:
                    # value in the alert is 'unchanged'
                    diff = 'unchanged'
                elif old_value.current_alert_condition_status['condition'] != current_value.current_alert_condition_status['condition'] or old_value.current_alert_condition_status['activated'] != current_value.current_alert_condition_status['activated']:
                    # value in the alert is 'changed'
                    diff = 'changed'
                else:
                    # value in the alert is 'unchanged'
                    diff = 'unchanged'

            # TODO Call this DTO AlertEvent
            diff_report.append({
                'diff_event': diff,
                'old': old_element,
                'current': current_element
            })

        current_element = None
        diff = 'lost'
        for old_key, old_value in old_alerts_state.iteritems():
            old_element = old_value
            if not current_alerts_state.has_key(old_key):
                diff_report.append({
                    'diff_event': diff,
                    'old': old_element,
                    'current': current_element
                })

        return diff_report


    def _group_by(self, diff_report, group_by):
        """Given reported alerts evaluation results. Consolidates them by the given key.
        For example: 1 mail with a list of alerts groups by destination, etc.
        :return a map, the key is the field 'group_by', the value is a list of alert evaluation results.
        """
        consolidated_map = {}

        for alert_event in diff_report:
            # get the available version of alert_evaluation_result
            alert_evaluation_result = alert_event['current']
            if alert_evaluation_result is None:
                alert_evaluation_result = alert_event['old']

            # calculate the group key
            if alert_evaluation_result.current_alert_condition_status is not None:
                key = alert_evaluation_result.current_alert_condition_status[group_by]
            if key is None:
                key = eval("alert_evaluation_result." + group_by)


            # and add the alert_event to the consolidated map
            if not consolidated_map.has_key(key):
                consolidated_map[key] = []
            consolidated_map[key].append(alert_event)
        return consolidated_map

    def _send_alerts_if_any(self, alerts_to_send_map):
        """Evaluate if there are news to send. If that is the case, send the alerts.
        This version only supports lists grouped by email."""
        for email_to_string, alert_event_list in alerts_to_send_map.iteritems():
            if not self._is_something_to_report(alert_event_list):
                continue
            html_version_main = self._html_version_main()
            html_version_items = self._html_version_items(alert_event_list)
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

            self._send_email(email, email_to_string)

    def _send_email(self, email, email_to_string):
        # send mail
        mail_server = smtplib.SMTP(host=self.smtp_server, port=self.smtp_port)
        if self.email_username is not None:
            mail_server.login(self.email_username, self.email_password)
        try:
            mail_server.sendmail(self.email_from, email_to_string, email.as_string())
            self.sent_emails_counter += 1
        finally:
            mail_server.close()

    def _html_version_items(self, alert_event_list):
        """transform each alert_event in html."""
        alert_event_style = {
            'new': 'background-color: lightcyan',
            'lost': 'background-color: lightgray',
            'changed': 'background-color: lightgreen',
            'unchanged':'background-color: white'}

        alert_condition_style = {
            'normal':'color: darkgreen',
            'warning':'color: darkorange',
            'critical':'color: darkred'
        }
        html = ''
        for alert_event in alert_event_list:
            # send alert_event only if something interesting happened.
            if alert_event['diff_event'] != 'unchanged' \
                    or alert_event['current'] is None \
                    or alert_event['current'].current_alert_condition_status is None \
                    or alert_event['current'].current_alert_condition_status['name'] != 'normal' \
                    or alert_event['old'] is None \
                    or alert_event['old'].current_alert_condition_status is None \
                    or alert_event['old'].current_alert_condition_status['name'] != 'normal':
                # TODO provide a better solution for undefined values
                variables = {
                    'old_target':'', 'old_alertName':'', 'old_title': '', 'old_value': '', 'old_condition':'',
                    'current_target':'', 'current_alertName':'', 'current_title': '', 'current_value': '', 'current_condition':'',
                    'alertName':'warning'
                }
                for version, alert_evaluation_result in {'old': alert_event['old'], 'current': alert_event['current']}.iteritems():
                    if alert_evaluation_result is not None and alert_evaluation_result.current_alert_condition_status is not None:
                        for k, v in alert_evaluation_result.current_alert_condition_status.iteritems():
                            variables[version + '_' + k] = v
                            # add known value in case 'old' or 'current' values are null, it keeps the last value
                            variables[k] = v
                        variables[version + '_target'] = alert_evaluation_result.target
                        variables[version + '_value'] = alert_evaluation_result.value
                        variables[version + '_alertName'] = alert_evaluation_result.current_alert_condition_status['name']
                        # variables['_date'] = datetime.datetime.now().strftime("%B %d, %Y"),
                        # variables['_time'] = datetime.datetime.now().strftime("%I:%M %p"),
                        # add known value in case 'old' or 'current' values are null, it keeps the last value
                        variables['target'] = alert_evaluation_result.target
                        variables['value'] = alert_evaluation_result.value
                        variables['alertName'] = alert_evaluation_result.current_alert_condition_status['name']
                variables['diff_event'] = alert_event['diff_event']

                # add styles for diff_event and alert event
                variables['alert_event_style'] = alert_event_style[variables['diff_event']]
                variables['alert_condition_style'] = alert_condition_style[variables['alertName']]

                html_item = self._html_version_item().format(**variables)
                html += html_item
        return html

    def _html_version_item(self):
        """html version of the list of alert_evaluation_result_list."""
        # TODO review where the template is stored and how path is solved
        # return self._get_content_of_resource_file("../data/html_version_item.html")
        return self._get_content_of_resource_file("html_version_item.html")

    def _html_version_main(self):
        """html version of the email. It must returns everything except "html_version_items"""
        # TODO review where the template is stored and how path is solved
        # return self._get_content_of_resource_file("../data/html_version_main.html")
        return self._get_content_of_resource_file("html_version_main.html")

    def get_sent_emails_counter(self):
        return self.sent_emails_counter

    def _is_something_to_report(self, alert_event_list):
        """Return True if the alert should be sent."""
        # TODO externalize this condition.
        for alert_event in alert_event_list:
            if alert_event['current'] is None:
                return True
            # elif alert_event['current'].current_alert_condition_status is None:
            #     return True
            else:
                if alert_event['current'].current_alert_condition_status['name'] != 'normal':
                    return True
            if alert_event['old'] is None:
                return True
            else:
                if alert_event['old'].current_alert_condition_status['name'] != 'normal':
                    return True
        return False

    def _get_content_of_resource_file(self, resource_file):
        """read the file from the package resource and returns its content. File must exists."""
        return pkg_resources.resource_string('grafana_alerts', resource_file)


class ConsoleAlertReporter:
    pass
