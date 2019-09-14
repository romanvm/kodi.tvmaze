# coding: utf-8
# Author: Roman Miroshnychenko aka Roman V.M.
# E-mail: roman1972@gmail.com

from __future__ import absolute_import
import inspect
import six
from contextlib import contextmanager
from platform import uname
from pprint import pformat
import xbmc
from .utils import logger


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
def debug_exception(logger_func=logger.error):
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

    :param logger_func: logger function which must accept a single argument
        which is a log message.
    """
    try:
        yield
    except Exception as exc:
        frame_info = inspect.trace(5)[-1]
        logger_func('*** Unhandled exception detected: {} {} ***'.format(type(exc), exc))
        logger_func('*** Start diagnostic info ***')
        logger_func('System info: {0}'.format(uname()))
        logger_func('OS info: {0}'.format(xbmc.getInfoLabel('System.OSVersionInfo')))
        logger_func('Kodi version: {0}'.format(
            xbmc.getInfoLabel('System.BuildVersion'))
        )
        logger_func('File: {0}'.format(frame_info[1]))
        context = ''
        if frame_info[4] is not None:
            for i, line in enumerate(frame_info[4], frame_info[2] - frame_info[5]):
                if i == frame_info[2]:
                    context += '{0}:>{1}'.format(str(i).rjust(5), line)
                else:
                    context += '{0}: {1}'.format(str(i).rjust(5), line)
        logger_func('Code context:\n' + context)
        logger_func('Global variables:\n' + _format_vars(frame_info[0].f_globals))
        logger_func('Local variables:\n' + _format_vars(frame_info[0].f_locals))
        logger_func('**** End diagnostic info ****')
        raise exc
