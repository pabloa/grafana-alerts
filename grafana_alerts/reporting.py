from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
    def __init__(self, email_from, smtp_server, smtp_port, email_username, email_password):
        self.email_from = email_from
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_username = email_username
        self.email_password = email_password

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
                key = eval("alert_evaluation_result.current_alert_condition_status['{group_by}']".format(group_by=group_by))
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
                                                    date=datetime.datetime.now().strftime("%B %d, %Y"),
                                                    time=datetime.datetime.now().strftime("%I:%M %p"),
                                                    companyName=""
            )
            # text_version = bs.get_text()

            # create email
            email = MIMEMultipart('alternative')
            # TODO calculate this value.
            email['Subject'] = "monitoring alert"
            email['From'] = self.email_from
            email_to = email_to_string.split(',')
            email['To'] = email_to
            # part_text = MIMEText(text_version, 'plain', 'utf-8')
            # email.attach(part_text)
            part_html = MIMEText(html_version, 'html', 'utf-8')
            email.attach(part_html)

            # send mail
            mail_server = smtplib.SMTP(host=self.smtp_server, port=self.smtp_port)
            mail_server.login(self.email_username, self.email_password)
            try:
                mail_server.sendmail(self.email_from, email_to, email.as_string())
            finally:
                mail_server.close()


    def _html_version_items(self, alert_evaluation_result_list):
        html = ''
        for alert_evaluation_result in alert_evaluation_result_list:
            variables = alert_evaluation_result.current_alert_condition_status.copy()
            variables['target'] = alert_evaluation_result.target
            variables['value'] = alert_evaluation_result.value
            variables['alertName'] = alert_evaluation_result.current_alert_condition_status['name']
            html_item = self._html_version_item().format(**variables)
            html += html_item
        return html

    def _html_version_item(self):
        # TODO externalize
        """html version of the list of alert_evaluation_result_list."""
        return """
<table width="900" class="alert_color_{alertName}">
    <tr>
        <td>
            {target} status is {alertName} for {title}
        </td>
    </tr>
    <tr>
        <td>
            value of {title}: {value} / {condition}
        </td>
    </tr>
</table>
"""


    def _html_version_main(self):
        # TODO externalize
        """html version of the email. It must returns everything except "html_version_items"""
        return """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>Alerts report</title>
</head>
<body style="font-family:'Helvetica Neue', Helvetica, Arial, sans-serif">
<table width="900" cellpadding="0" cellspacing="0" align="center" border="0">
    <tr height="80px" bgcolor="#D1E7F2">
        <td style="padding-left:10px"><font size="+3" style="font-weight:bold;">Alert report</font></td>
        <td align="right" style="padding-right:10px"><font size="+1" style="font-weight:bold;">{date} {time}</font></td>
    </tr>
</table>
<div style="height:10px"></div>
<table width="900" cellpadding="0" cellspacing="0" align="center" border="0">
    <tr height="5px" bgcolor="#cff293">
        <!--<td><img src="images/image.png" width="900" height="200" /></td>-->
        <td></td>
    </tr>
</table>
<div style="height:10px"></div>
<table width="900" cellpadding="0" cellspacing="0" align="center" border="0">
    <tr>
        <td align="justify">{html_version_items}
            <!--<br /><br /><a href="#">Read More</a><br /><br />-->
        </td>
    </tr>
</table>
<div style="height:10px"></div>
<table width="900" cellpadding="0" cellspacing="0" align="center" border="0">
    <tr height="5px" bgcolor="#cff293">
        <!--<td><img src="images/image.png" width="900" height="200" /></td>-->
        <td></td>
    </tr>
</table>
<div style="height:10px"></div>
<table width="900" cellpadding="0" cellspacing="0" align="center" border="0">
    <tr bgcolor="#8DBDD4" style="color:#ffffff">
    <td align="left" style="padding-left:10px; padding-top:15px; padding-bottom:15px;" valign="top"><font size="+1" style="font-weight:bold; color:#000000">{companyName}</font><br />
        <!--.--></td>
</table>
<div style="height:10px"></div>
</body>
</html>
"""


class ConsoleAlertReporter:
    pass