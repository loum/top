__all__ = [
    "BaseD",
]
import os
from optparse import OptionParser


class BaseD(object):
    """Nparcel base daemoniser.

    .. attribute:: config

        location of the daemon configuration file

    .. attribute:: usage

        program usage

    .. attribute:: parser

        handle to a :class:`optparse.OptionParser` object

    .. attribute:: options

        object containing values for all options

    .. attribute:: args

        list of positional arguments leftover after parsing options

    .. attribute:: command

        the command to execute

    """
    _config = os.path.join(os.path.expanduser('~'),
                           '.nparceld',
                           'nparceld.conf')
    _usage = 'usage: %prog [options] start|stop|status'
    _parser = OptionParser(usage=_usage)

    def __init__(self):
        """Nparcel BaseD initialisation.
        """
        self._parser.add_option("-v", "--verbose",
                                dest="verbose",
                                action="count",
                                default=0,
                                help="raise logging verbosity")
        self._parser.add_option('-d', '--dry',
                                dest='dry',
                                action='store_true',
                                help='dry run - report only, do not execute')
        self._parser.add_option('-c', '--config',
                                dest='config',
                                default=self._config,
                                help=('override default config "%s"' %
                                      self._config))

    @property
    def config(self):
        return self._config

    def set_config(self, value):
        self._config = value

    @property
    def usage(self):
        return self._usage

    def set_usage(self, value):
        self._usage = value
        self._parser.set_usage(value)

    @property
    def parser(self):
        return self._parser

    @property
    def options(self):
        return self._options

    def set_options(self, value):
        self._options = value

    @property
    def args(self):
        return self._args

    def set_args(self, value):
        self._args = value

    @property
    def command(self):
        return self._command

    def set_command(self, value):
        self._command = value

    def check_args(self):
        """Verify that the daemon arguments are as expected.

        Sets the controller action (for example stop, start or status).

        Attempts to make a sane assesment of options against the given
        :attr:`command`.

        **Raises**:
            ``SystemExit`` (program exit) if one argument is not provided
            on the command line

        """
        (options, args) = self.parser.parse_args()
        self.set_options(options)
        self.set_args(args)

        if len(self.args) != 1:
            self.parser.error("incorrect number of arguments")

        self.set_command(self.args[0])

        if self.command != 'start' and self.options.dry:
            self.parser.error('invalid option(s) with command "%s"' %
                              self.command)
