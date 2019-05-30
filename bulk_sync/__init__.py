import logging

from django.db import transaction
from bulk_update.helper import bulk_update

logger = logging.getLogger(__name__)


def bulk_sync(new_models, key_fields, filters, batch_size=None):
    """ Combine bulk create, update, and delete.  Make the DB match a set of in-memory objects.

    `new_models`: Django ORM objects that are the desired state.  They may or may not have `id` set.
    `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows.  If a foreign key
            is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`.
    `filters`: Q() filters specifying the subset of the database to work in.
    `batch_size`: passes through to Django `bulk_create.batch_size` and `bulk_update.batch_size`, and controls
            how many objects are created/updated per SQL query.

    """
    db_class = new_models[0].__class__

    with transaction.atomic():
        objs = db_class.objects.all()
        if filters:
            objs = objs.filter(filters)
        objs = objs.only('pk', *key_fields).select_for_update()

        def get_key(obj):
            return tuple(getattr(obj, k) for k in key_fields)

        obj_dict = {}
        for obj in objs:
            obj_dict[get_key(obj)] = obj

        new_objs = []
        existing_objs = []
        for new_obj in new_models:
            old_obj = obj_dict.pop(get_key(new_obj), None)
            if old_obj is None:
                # This is a new object, so create it.
                new_objs.append(new_obj)
            else:
                new_obj.id = old_obj.id
                existing_objs.append(new_obj)

        db_class.objects.bulk_create(new_objs, batch_size=batch_size)

        bulk_update(existing_objs, batch_size=batch_size)

        # delete stale ones...
        objs.filter(pk__in=[_.pk for _ in list(obj_dict.values())]).delete()

        assert len(existing_objs) == len(new_models) - len(new_objs)

        stats = {'created': len(new_objs), 'updated': len(new_models) - len(new_objs), 'deleted': len(obj_dict)}

        logger.debug(
            "{}: {} created, {} updated, {} deleted.".format(
                db_class.__name__, stats['created'], stats['updated'], stats['deleted']
            )
        )

    return {'stats': stats}
