.. Nparcel B2C Primary Elect

.. toctree::
    :maxdepth: 2

Nparcel Primary Elect
=====================
*New in version 0.14*

Primary Elect is a service provided to the customer that allows them
to nominate the Alternate Delivery Point from where they can pick up
their parcels.

Primary Elect jobs differ from the normal Nparcel flow in that the jobs
are not triggerred by a failed delivery event.  Instead, jobs are sent
directly from the vendor (for example, Grays Online)

.. note::

    Current arrangement is a short-term solution to enable the Primary
    Elect service option whilst the various Business Units update their
    systems to accommodate such requests in the future.

The following diagram describes various interfaces:

.. image:: ../_static/pe_overview.png
    :align: center
    :alt: Nparcel B2C Primary Elect Interfaces

*The Nparcel B2C Primary Elect workflow*

Primary Elect jobs involve two additional interfaces to the normal Nparcel
workflow:

* Raw WebMethods files from Toll GIS

* MTS Data Warehouse

Nparcel Primary Elect Workflow
------------------------------

Raw WebMethods T1250 Files -- GIS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Since the various Business Units do not support Primary Elect jobs,
Nparcel receives a direct feed from the GIS-prepared WebMethods interface.
Nparcel uses the :mod:`nparcel.mapper` middleware component to translate
the WebMethods format into typical Nparcel T1250.

The :mod:`mapper` workflow starts with the ``npmapperd`` script.
First, ``npmapperd`` will check for WebMethods raw T1250 and attempts to
translated these into Nparcel T1250 format.  From here, the translated
T1250 files are deposited into the corresponding Business Unit inbound
FTP resource directories where they enter into the normal Nparcel
workflow.

.. note::

    Translated Nparcel T1250 files that are processed by ``nploaderd``
    **will not** generate comms files

Some notable functionality provided by the translation process:

* pre-populates the *Service Code* field (offset 842) with the value ``3``
  which represents a Primary Elect job type

``npmapperd`` Configuration Items
*********************************

:mod:`nparcel.mapper` uses the standard ``nparceld.conf`` configuration
file to define the WebMethods interface.  The following list details
the required configuration options:

* ``pe_in`` (default ``/var/ftp/pub/nparcel/gis/in``)

    As with the other Business Units, inbound file from GIS are transfered
    via FTP.  ``pe_in`` represents the FTP resource that files are deposited
    to and where the ``mapper`` looks for files to process.

    .. note::

        As with the other FTP interfaces, the FTP resource needs to be
        created as per `these instructions <vsftpd.html>`_

* ``pe_loop`` (default 30 (seconds))

    Control mapper daemon facility sleep period between inbound file checks.

* ``file_format`` (default ``T1250_TOL[PIF]_\d{14}\.dat``)

    File format represents the filename structure to parse for Primary Elect
    inbound.  This was prepared during development so it may change later
    on.  Better to adjust it via config then in code.

* ``file_archive_string`` (default ``T1250_TOL[PIF]_(\d{8})\d{6}\.dat``)
    Each T1250 should contain a YYYYMMDD sequence that defines date.  This
    is used by the archiver.  The file_archive_string captures the regular
    expression grouping that defines the date.

* ``customer`` (default ``gis``)
    Upstream provider of the T1250 files.

``npmapperd`` usage
*******************

``npmapper`` can be configured to run as a daemon as per the following::

    $ npmapperd -h
    usage: npmapperd [options] start|stop|status
    
    options:
      -h, --help            show this help message and exit
      -v, --verbose         raise logging verbosity
      -d, --dry             dry run - report only, do not execute
      -b, --batch           single pass batch mode
      -c CONFIG, --config=CONFIG
                              override default config
                              "/home/guest/.nparceld/nparceld.conf"
      -f FILE, --file=FILE  file to process inline (start only)

MTS Delivery Report Files
^^^^^^^^^^^^^^^^^^^^^^^^^

In order to generate customer notification comms the :mod:`mapper` needs
to interogate the MTS system to capture job delivery times.

MTS is a readonly data warehouse that provides a static view of all
driver deliveries.  The interface is refreshed daily with new data
being provided around midday.

MTS Delivery Report Configuration Items
***************************************

As a separate process, MTS Delivery Report extraction configuration
items are managed in a separate configuration file, ``npmts.conf``:

* ``db``
    Holds the MTS database credentials in the following format::

        host = host
        user = user
        password = password
        port =  1521
        sid = sid

* ``report_range`` (default ``7`` (days))

    number of days that the report should cover

* ``display_headers`` (default ``yes``)

    will add the column names to the CSV if set to ``yes``

* ``out_dir`` (default ``/data/nparcel/mts``)

    controls where the CSV report files are written

* ``file_cache`` (default ``10``)

    file_cache is the number of report files to maintain before
    purging from the file system

``npmts`` usage
***************

.. note::
    the MTS delivery report takes around 10 minutes to run.  The actual
    SQL can be seen in the template file ``~/.nparceld/templates/mts_sql.t``

Although built on top of the daemoniser facilty, it makes sense
to run ``npmts`` in batch mode::

    $ npmts -h
    usage: npmts [options]
    
    options:
      -h, --help            show this help message and exit
      -v, --verbose         raise logging verbosity
      -d, --dry             dry run - report only, do not execute
      -b, --batch           single pass batch mode
      -c CONFIG, --config=CONFIG
                            override default config
                            "/home/guest/.nparceld/npmts.conf"
      -t TEMPLATE_DIR, --template_dir=TEMPLATE_DIR
                            location of SQL template files

Since the availability of MTS delivery report files can occur at any time
up to midday, the safest option is to create a spread of runs similar to
the following::

     0 9,12,14 * * * /usr/local/bin/npmts
  
.. note::
    the above crontab entry will generate a MTS delivery report
    every day at 9AM, midday and 2PM

Primary Elect Nofitications
^^^^^^^^^^^^^^^^^^^^^^^^^^^
In a similar fashion to the ``npreminderd`` process, Primary Elect
consumer notifications are managed by a separate process,
``npprimaryelectd``.

``npprimaryelectd`` identifies all Primary Elect jobs whose job items
have not had their ``jobitem.notify_ts`` column set and cross references
the connote entries against those within the output produced by the MTS
Delivery Report.  Connotes that appear in the MTS Delivery Report with
a valid ``Actually Arrived`` entry triggers cnotification comms.

``npprimaryelectd`` Configuration Items
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* ``inbound_mts`` (default ``/data/nparcel/mts``)

    the MTS Delivery Report directory.

* ``mts_filename_format`` (default ``mts_delivery_report_\d{14}\.csv``)

    the MTS Delivery Report filename format as expressed as a Python
    regular expression string.

``npprimaryelectd`` usage
^^^^^^^^^^^^^^^^^^^^^^^^^

Although ``npprimaryelectd`` can be run as a daemon, it does not make
sense since its feeder stream only provides fresh data at most once per
day.  Therefore, align ``npprimaryelectd`` with ``npmts``::

    $ npprimaryelectd -h
    usage: npprimaryelectd [options] start|stop|status
    
    options:
      -h, --help            show this help message and exit
      -v, --verbose         raise logging verbosity
      -d, --dry             dry run - report only, do not execute
      -b, --batch           single pass batch mode
      -c CONFIG, --config=CONFIG
                            override default config
                            "/home/guest/.nparceld/nparceld.conf"
      -f FILE, --file=FILE  file to process inline (start only)