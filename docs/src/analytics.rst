******************
Analytics
******************

We aggregate our analytics data with

.. code-block:: bash

    lunes-cms-cli aggregate_analytics

This script does the following actions:

* Aggregate data from `analytics_analyticsevent` table
* Send the data to grafana: https://grafana.tuerantuer.org/
* Delete aggregated data (currently disabled for testing purposes)

The script runs as a crontab on the server every night at 2am.

Local testing
=============

* get the ca, client.crt and client.key from the lunes test server

.. code-block:: bash

    ssh username@lunes-test.tuerantuer.org "sudo cat /etc/pki/client.crt" > client.crt
    ssh username@lunes-test.tuerantuer.org "sudo cat /etc/pki/client.key" > client.key
    ssh username@lunes-test.tuerantuer.org "cat /usr/local/share/ca-certificates/ca.crt" > ca.crt

* create a local `lunes-cms.ini` in the root folder and override variables

.. code-block:: ini

    [influxdb]
    INFLUX_URL = https://monitoring.tuerantuer.org/write
    INFLUX_DB = lunes_test
    INFLUX_CERT = /path/to/lunes-cms/example-configs/client.crt
    INFLUX_KEY = /path/to/lunes-cms/example-configs/client.key
    INFLUX_CA = /path/to/lunes-cms/example-configs/ca.crt

* run:

.. code-block:: bash

    lunes-cms-cli aggregate_analytics --dry-run
    lunes-cms-cli aggregate_analytics
