# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: roman1972@gmail.com

import inspect
import six
from contextlib import contextmanager
from platform import uname
from pprint import pformat
import xbmc


def _logger(message, level=xbmc.LOGERROR):
    if isinstance(message, six.text_type):
        message.encode('utf-8')
    xbmc.log(message, level)


def _format_vars(variables):
    """
    Format variables dictionary
    :param variables: variables dict
    :type variables: dict
    :return: formatted string with sorted ``var = val`` pairs
    :rtype: str
    """
    var_list = [(var, val) for var, val in six.iteritems(variables)]
    lines = []
    for var, val in sorted(var_list, key=lambda i: i[0]):
        if not (var.startswith('__') or var.endswith('__')):
            lines.append('{0} = {1}'.format(var, pformat(val)))
    return '\n'.join(lines)


@contextmanager
def debug_exception(logger=None):
    """
    Diagnostic helper context manager
    It controls execution within its context and writes extended
    diagnostic info to the Kodi log if an unhandled exception
    happens within the context. The info includes the following items:
    - System info
    - Kodi version
    - Module path.
    - Code fragment where the exception has happened.
    - Global variables.
    - Local variables.
    After logging the diagnostic info the exception is re-raised.
    Example::
        with debug_exception():
            # Some risky code
            raise RuntimeError('Fatal error!')
    :param logger: logger function which must accept a single argument
        which is a log message. By default it is :func:`xbmc.log`
        with ``ERROR`` level.
    """
    try:
        yield
    except Exception as exc:
        if logger is None:
            logger = _logger
        frame_info = inspect.trace(5)[-1]
        logger('Unhandled exception detected: {}'.format(exc))
        logger('*** Start diagnostic info ***')
        logger('System info: {0}'.format(uname()))
        logger('OS info: {0}'.format(xbmc.getInfoLabel('System.OSVersionInfo')))
        logger('Kodi version: {0}'.format(
            xbmc.getInfoLabel('System.BuildVersion'))
        )
        logger('File: {0}'.format(frame_info[1]))
        context = ''
        if frame_info[4] is not None:
            for i, line in enumerate(frame_info[4], frame_info[2] - frame_info[5]):
                if i == frame_info[2]:
                    context += '{0}:>{1}'.format(str(i).rjust(5), line)
                else:
                    context += '{0}: {1}'.format(str(i).rjust(5), line)
        logger('Code context:\n' + context)
        logger('Global variables:\n' + _format_vars(frame_info[0].f_globals))
        logger('Local variables:\n' + _format_vars(frame_info[0].f_locals))
        logger('**** End diagnostic info ****')
        raise exc
