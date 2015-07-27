Grafana Alert Module
====================

grafana-alerts Collects stats from a grafana server based on information available
from the Grafana Dashboards. Then compare those values to an alert table and
throws alert emails if the case is needed.

Sites
-----

Installation package: https://pypi.python.org/pypi/grafana_alerts

Project Home: https://github.com/pabloa/grafana-alerts

Issues and bugs: https://github.com/pabloa/grafana-alerts/issues


Installation
------------
::

    sudo pip install grafana-alerts

if you get an error, perhaps it is because the version available is a development
version. In this case try with::

    sudo pip install --pre grafana-alerts



Configuration
-------------

Create a file /etc/grafana_alerts/grafana_alerts.cfg
with::

    #
    # Grafana alerts configuration file.
    #

    # The URL where grafana server is listening. It must finish with the character '/' (default value: http://localhost:3130)
    grafana_url = http://yourgrafanaserver.com/grafana/

    # Grafana token with viewer access (default value: empty string)
    grafana_token = qwertysDssdsfsfsdfSFsfsfEWrwrwERwrewrwrWeRwRwerWRwERwerWRwerweRwrEWrWErwerWeRwRwrewerr==

    # email to use as alert sender (default value: grafana-alert@localhost)
    email_from = alert@example.com

    # smtp server to use (default value: localhost)
    smtp_server = localhost

    # smtp server host to use (default value: 25)
    # if port is not 25, starts a tls session.
    smtp_port = 25

    # smtp server username to use if it is needed. Optional. Leave it commented if not used. (default value: no username)
    #smtp_username = my_smtp_username

    # smtp server password to use if it is needed. Optional. Leave it commented if not used. (default value: no password)
    #smtp_password = my_smtp_password


Add a cron task to execute grafana_alerts for example each 3 minutes:::

    */3 * * * *     grafana_alerts


Monitoring Dashboards
---------------------

Dashboards to be monitored for alerts must be marked with the tag "monitored"

In each monitored Dashboard, add a text panel with title 'alerts' and a description of your alerts. For example:::

    50<=x<=100; normal; server@example.com

    35<x<50; warning; server-mantainers@example.com

    x<=35; critical; server-mantainers@example.com, sysop@example.com


Notes:

* values depend of the graph in that dashboard.
* x is mandatory.

Here is an example: 

https://drive.google.com/a/ailive.net/file/d/0B1LiPvzYYFN0TTlBRnFlTG5Ya1E/view?pli=1

Changes
-------

Version 1.0.0.dev7:

* [FIXED] https://github.com/pabloa/grafana-alerts/issues/7 KeyError: 'hide'

Version 1.0.0.dev6:

* [FIXED] https://github.com/pabloa/grafana-alerts/issues/4 Runtime error when a grafana metric has not values.
* [MINOR] renamed variables. Minor changes in emails.