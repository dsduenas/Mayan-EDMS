from __future__ import absolute_import

import logging

from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver

from haystack.management.commands.update_index import Command

from navigation.api import register_sidebar_template, register_links
from documents.models import Document
from scheduler.runtime import scheduler
from signaler.signals import post_update_index, pre_update_index
from scheduler.api import register_interval_job
from lock_manager import Lock, LockError

from .models import IndexableObject
from .conf.settings import INDEX_UPDATE_INTERVAL

logger = logging.getLogger(__name__)

search = {'text': _(u'search'), 'view': 'search', 'famfam': 'zoom'}

register_sidebar_template(['search'], 'search_help.html')

register_links(['search'], [search], menu_name='form_header')

register_sidebar_template(['search'], 'recent_searches.html')

Document.add_to_class('mark_indexable', lambda obj: IndexableObject.objects.mark_indexable(obj))


@receiver(post_update_index, dispatch_uid='clear_pending_indexables')
def clear_pending_indexables(sender, **kwargs):
    logger.debug('Clearing all indexable flags post update index signal')
    IndexableObject.objects.clear_all()


@receiver(pre_update_index, dispatch_uid='scheduler_shutdown_pre_update_index')
def scheduler_shutdown_pre_update_index(sender, **kwargs):
    logger.debug('Scheduler shut down on pre update index signal')
    scheduler.shutdown()


def search_index_update():
    lock_id = u'search_index_update'
    try:
        logger.debug('trying to acquire lock: %s' % lock_id)
        lock = Lock.acquire_lock(lock_id)
        logger.debug('acquired lock: %s' % lock_id)

        logger.debug('Executing haystack\'s index update command')
        command = Command()
        command.handle()

        lock.release()
    except LockError:
        logger.debug('unable to obtain lock')
        pass
    
    
register_interval_job('search_index_update', _(u'Update the search index with the most recent modified documents.'), search_index_update, seconds=INDEX_UPDATE_INTERVAL)




