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
        objs = objs.only("pk", *key_fields).select_for_update()

        def get_key(obj):
            return tuple(getattr(obj, k) for k in key_fields)

        obj_dict = {get_key(obj): obj for obj in objs}

        new_objs = []
        existing_objs = []
        for new_obj in new_models:
            old_obj = obj_dict.pop(get_key(new_obj), None)
            if old_obj is None:
                # This is a new object, so create it.
                # Make sure the primary key field is clear.
                new_obj.pk = None
                new_objs.append(new_obj)
            else:
                new_obj.id = old_obj.id
                existing_objs.append(new_obj)

        db_class.objects.bulk_create(new_objs, batch_size=batch_size)

        bulk_update(existing_objs, batch_size=batch_size)

        # delete stale ones...
        objs.filter(pk__in=[_.pk for _ in list(obj_dict.values())]).delete()

        assert len(existing_objs) == len(new_models) - len(new_objs)

        stats = {"created": len(new_objs), "updated": len(new_models) - len(new_objs), "deleted": len(obj_dict)}

        logger.debug(
            "{}: {} created, {} updated, {} deleted.".format(
                db_class.__name__, stats["created"], stats["updated"], stats["deleted"]
            )
        )

    return {"stats": stats}


def bulk_compare(old_models, new_models, key_fields, ignore_fields=None):
    """ Compare two sets of models by `key_fields`.
    `old_models`: Iterable of Django ORM objects to compare.
    `new_models`: Iterable of Django ORM objects to compare.

    `ignore_fields`: (optional) If set, provide field names that should not be considered when comparing objects.

    Returns: dict of
        'added': list of all added objects.
        'unchanged': list of all unchanged objects.
        'updated': list of all updated objects.
        'updated_details': dict of {obj: {field_name: (old_value, new_value)}} for all changed fields in each updated object.
        'removed': list of all removed objects.

    """

    def get_key(obj):
        return tuple(getattr(obj, k) for k in key_fields)

    old_obj_dict = {get_key(obj): obj for obj in old_models}

    new_objs = []
    existing_objs = []
    change_details = {}
    updated_objs = []
    unchanged_objs = []

    for new_obj in new_models:
        old_obj = old_obj_dict.pop(get_key(new_obj), None)
        if old_obj is None:
            # This is a new object, so create it.
            # Make sure the primary key field is clear.
            new_obj.pk = None
            new_objs.append(new_obj)
        else:
            new_obj.id = old_obj.id

            cmp_result = compare_objs(old_obj, new_obj, ignore_fields)
            if cmp_result:
                updated_objs.append(new_obj)
                change_details[new_obj] = cmp_result
            else:
                unchanged_objs.append(new_obj)

            existing_objs.append(new_obj)

    return {
        "added": new_objs,
        "unchanged": existing_objs,
        "updated": updated_objs,
        "updated_details": change_details,
        "removed": old_obj_dict.values(),
    }


def compare_objs(obj1, obj2, ignore_fields=None):
    """ Compare two Django ORM objects (presumably of the same model class).

    `obj1`: The first object to compare.
    `obj2`: The second object to compare.
    `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows.  If a foreign key
            is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`.
    `ignore_fields`: (optional) If set, provide field names that should not be considered when comparing objects.

    Returns: dict of changed fields and their old/new values: {field_name: (old_value, new_value)}
    """

    ret = {}
    fields = obj1._meta.get_fields()
    for f in fields:
        if ignore_fields and f.name in ignore_fields:
            continue

        v1 = f.to_python(getattr(obj1, f.name))
        v2 = f.to_python(getattr(obj2, f.name))
        if v1 != v2:
            ret[f.name] = (v1, v2)

    return ret
