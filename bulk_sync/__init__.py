from collections import OrderedDict, defaultdict
import logging
import functools

from django.db import transaction, router
from django.core.exceptions import FieldDoesNotExist

logger = logging.getLogger(__name__)


def bulk_sync(
    new_models,
    key_fields,
    filters,
    batch_size=None,
    fields=None,
    exclude_fields=None,
    skip_creates=False,
    skip_updates=False,
    skip_deletes=False,
    db_class=None,
    select_for_update_of=None,
):
    """Combine bulk create, update, and delete.  Make the DB match a set of in-memory objects.

    `new_models`: Django ORM objects that are the desired state.  They may or may not have `id` set.
    `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows.  If a foreign key
            is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`.
    `filters`: Q() filters specifying the subset of the database to work in. Use `None` or `[]` if you want to sync
            against the entire table.
    `batch_size`: (optional) passes through to Django `bulk_create.batch_size` and `bulk_update.batch_size`, and controls
            how many objects are created/updated per SQL query.
    `fields`: (optional) list of fields to update. If not set, will sync all fields that are editable and not
            auto-created.
    `exclude_fields`: (optional) list of fields to exclude from updates. Subtracts from the passed-in `fields` or
            default-calculated `fields` (see `fields` documentation above.)
    `skip_creates`: If truthy, will not perform any object creations needed to fully sync. Defaults to not skip.
    `skip_updates`: If truthy, will not perform any object updates needed to fully sync. Defaults to not skip.
    `skip_deletes`: If truthy, will not perform any object deletions needed to fully sync. Defaults to not skip.
    `db_class`: (optional) Model class to operate on. If new_models always contains at least one object, this can
            be set automatically so is optional.
    `select_for_update_of`: (optional) Iterable passed directly to select_for_update `of` clause to control locking of related models.
            See https://docs.djangoproject.com/en/dev/ref/models/querysets/#select-for-update for more information.
    """

    if db_class is None:
        try:
            db_class = new_models[0].__class__
        except IndexError:
            try:
                db_class = new_models.model
            except AttributeError:
                db_class = None

    if db_class is None:
        raise RuntimeError(
            "Unable to identify model to sync. Need to provide at least one object in `new_models`, provide "
            "`db_class`, or set `new_models` with a queryset like `db_class.objects.none()`."
        )

    if fields is None:
        # Get a list of fields that aren't PKs and aren't editable (e.g. auto_add_now) for bulk_update
        fields = [
            field.name
            for field in db_class._meta.fields
            if not field.primary_key and not field.auto_created and field.editable
        ]

    if exclude_fields is not None:
        model_fields = set(field.name for field in db_class._meta.fields)
        fields_to_update = set(fields)
        fields_to_exclude = set(exclude_fields)

        # Check that we're not attempting to exclude non-existent fields
        if not fields_to_exclude <= model_fields:
            raise FieldDoesNotExist(f'model "{db_class.__name__}" has no field(s) {fields_to_exclude - model_fields}')

        fields = list(fields_to_update - fields_to_exclude)

    using = router.db_for_write(db_class)
    with transaction.atomic(using=using):
        objs = db_class.objects.all()
        if filters:
            objs = objs.filter(filters)

        ofargs = {}
        if select_for_update_of:
            ofargs = {"of": select_for_update_of}

        objs = objs.only("pk", *key_fields).select_for_update(**ofargs).order_by("pk")

        prep_functions = defaultdict(lambda: lambda x: x)
        prep_functions.update(
            {
                field.name: functools.partial(field.to_python)
                for field in (db_class._meta.get_field(k) for k in key_fields)
                if hasattr(field, "to_python")
            }
        )

        def get_key(obj, prep_values=False):
            return tuple(prep_functions[k](getattr(obj, k)) if prep_values else getattr(obj, k) for k in key_fields)

        obj_dict = {get_key(obj): obj for obj in objs}

        new_objs = []
        existing_objs = []
        for new_obj in new_models:
            old_obj = obj_dict.pop(get_key(new_obj, prep_values=True), None)
            if old_obj is None:
                # This is a new object, so create it.
                new_objs.append(new_obj)
            else:
                new_obj.pk = old_obj.pk
                existing_objs.append(new_obj)

        if not skip_creates:
            db_class.objects.bulk_create(new_objs, batch_size=batch_size)

        if not skip_updates:
            db_class.objects.bulk_update(existing_objs, fields=fields, batch_size=batch_size)

        if not skip_deletes:
            # delete stale objects
            objs.filter(pk__in=[_.pk for _ in list(obj_dict.values())]).delete()

        assert len(existing_objs) == len(new_models) - len(new_objs)

        stats = {
            "created": 0 if skip_creates else len(new_objs),
            "updated": 0 if skip_updates else (len(new_models) - len(new_objs)),
            "deleted": 0 if skip_deletes else len(obj_dict),
        }

        logger.debug(
            "{}: {} created, {} updated, {} deleted.".format(
                db_class.__name__, stats["created"], stats["updated"], stats["deleted"]
            )
        )

    return {"stats": stats}


def bulk_compare(old_models, new_models, key_fields, ignore_fields=None):
    """Compare two sets of models by `key_fields`.
    `old_models`: Iterable of Django ORM objects to compare.
    `new_models`: Iterable of Django ORM objects to compare.
    `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows.  If a foreign key
            is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`.
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

    old_obj_dict = OrderedDict((get_key(obj), obj) for obj in old_models)

    new_objs = []
    change_details = {}
    updated_objs = []
    unchanged_objs = []

    for new_obj in new_models:
        old_obj = old_obj_dict.pop(get_key(new_obj), None)
        if old_obj is None:
            # This is a new object, so create it.
            new_objs.append(new_obj)
        else:
            new_obj.pk = old_obj.pk

            cmp_result = compare_objs(old_obj, new_obj, ignore_fields)
            if cmp_result:
                updated_objs.append(new_obj)
                change_details[new_obj] = cmp_result
            else:
                unchanged_objs.append(new_obj)

    return {
        "added": new_objs,
        "unchanged": unchanged_objs,
        "updated": updated_objs,
        "updated_details": change_details,
        "removed": old_obj_dict.values(),
    }


def compare_objs(obj1, obj2, ignore_fields=None):
    """Compare two Django ORM objects (presumably of the same model class).

    `obj1`: The first object to compare.
    `obj2`: The second object to compare.
    `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows.  If a foreign key
            is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`.
    `ignore_fields`: (optional) If set, provide field names that should not be considered when comparing objects.
            If a foreign key is being used as an ignore_field, be sure to pass the `fieldname_id` rather than the `fieldname`.

    Returns: dict of changed fields and their old/new values: {field_name: (old_value, new_value)}
    """

    ret = {}
    fields = obj1._meta.get_fields()
    for f in fields:
        if ignore_fields and f.attname in ignore_fields:
            continue

        v1 = f.to_python(getattr(obj1, f.attname))
        v2 = f.to_python(getattr(obj2, f.attname))
        if v1 != v2:
            ret[f.name] = (v1, v2)

    return ret
