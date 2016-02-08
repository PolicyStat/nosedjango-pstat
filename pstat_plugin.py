import logging
import os.path

from nosedjango.plugins.base_plugin import Plugin


class PstatPlugin(Plugin):
    name = 'pstat'

    def beforeTestSetup(self, settings, setup_test_environment, connection):
        logging.getLogger().setLevel(logging.WARNING)
        switched_settings = {
            'DOCUMENT_IMPORT_STORAGE_DIR': 'document_import%(token)s',
            'DOCUMENT_SETTINGS_STORAGE_DIR': 'document_settings%(token)s',
            'ATTACHMENT_STORAGE_PREFIX': 'attachments%(token)s',
            'MAILER_LOCKFILE': 'send_mail%(token)s',
        }
        settings.DOCUMENT_PRINTING_CACHE_ON_SAVE = False

        token = self.get_unique_token()
        for key, value in switched_settings.items():
            setattr(settings, key, value % {'token': token})
        settings.CACHE_BACKEND = 'locmem://'
        settings.DISABLE_QUERYSET_CACHE = True

    def beforeFixtureLoad(self, settings, test):
        """
        Need to wait until after beforeTestSetup is called in case the
        NoseDjango FileStoragePlugin is being used to give us an isolated
        media directory.

        Every test needs a new unique folder to avoid collisions.
        """
        from django.core.cache import cache
        cache.clear()

        self.change_storage_settings(settings)

    def change_storage_settings(self, settings):
        """
        Update all of the file storage paths to use our test directory and to
        be served from the proper URL.
        """
        from django.core.files.storage import default_storage

        from pstat.printing.conf import settings as print_settings
        from pstat.document_backup.conf import settings as backup_settings
        from django.core.files.storage import FileSystemStorage

        # Can't use the normal switched_settings dict because these settings
        # live outside of the django default settings
        token = self.get_unique_token()
        if print_settings.PDF_STORAGE_BACKEND is FileSystemStorage:
            # Update the storage settings to use absolute paths or urls
            # relative to the current media settings
            storage_dir = 'pdf_cache/'
            storage_dir = os.path.abspath(
                os.path.join(default_storage.location, storage_dir))
            print_settings.PDF_STORAGE_DIR = storage_dir
        else:
            # Boto and other non-filesystem don't need absolute paths and urls
            # They do need a unique subdirectory path though, because the
            # NoseDjango FileStoragePlugin can't reliably empty a directory on
            # S3
            storage_dir = 'pdf_cache%s/' % token
            print_settings.PDF_STORAGE_DIR = storage_dir

        if backup_settings.STORAGE_BACKEND is FileSystemStorage:
            storage_dir = 'document_backup/'
            storage_dir = os.path.abspath(
                os.path.join(default_storage.location, storage_dir))
            backup_settings.STORAGE_DIR = storage_dir
        else:
            # Boto and other non-filesystem don't need absolute paths and urls
            # They do need a unique subdirectory path though, because the
            # NoseDjango FileStoragePlugin can't reliably empty a directory on
            # S3
            storage_dir = 'document_backup%s/' % token
            backup_settings.STORAGE_DIR = storage_dir
