# django-bulk-sync

Combine bulk create, update, and delete into a single call.

`django-bulk-sync` is a package for the Django ORM that combines bulk_create, bulk_update, and delete into a single method call to `bulk_sync`.

It manages all necessary creates, updates, and deletes with as few database calls as possible to maximize performance.

It can use either database PKs or `key_fields` to match up objects with existing records.

## Installation

The package is available on pip as [django-bulk-sync][django-bulk-sync]. Run:

`pip install django-bulk-sync`

then import via:

`from bulk_sync import bulk_sync`

## A Usage Scenario

Companies have zero or more Employees. You want to efficiently sync the names of all employees for a single `Company` from an import from that company, but some are added, updated, or removed. The simple approach is inefficient -- read the import line by line, and:

For each of N records:

-   SELECT to check for the employee's existence
-   UPDATE if it exists, INSERT if it doesn't

Then figure out some way to identify what was missing and delete it. As is so often the case, the speed of this process is controlled mostly by the number of queries run, and here it is about two queries for every record, and so O(N).

Instead, with `bulk_sync`, we can avoid the O(N) number of queries, and simplify the logic we have to write as well.

## Example Usage

```python
from django.db.models import Q
from bulk_sync import bulk_sync

new_models = []
for line in company_import_file:
	# The `.id` (or `.pk`) field should not be set. Instead, `key_fields`
	# tells it how to match.
	e = Employee(name=line['name'], phone_number=line['phone_number'], ...)
	new_models.append(e)

# `filters` controls the subset of objects considered when deciding to
# update or delete.  Here we sync only company 501 employees.
filters = Q(company_id=501)

# `key_fields` matches an existing object if all `key_fields` are equal.
key_fields = ('name', )

ret = bulk_sync(
        new_models=new_models,
        filters=filters,
        fields=['name', 'phone_number', ...],
        key_fields=key_fields)

print("Results of bulk_sync: "
      "{created} created, {updated} updated, {deleted} deleted."
      		.format(**ret['stats']))
```

Under the hood, it will atomically call `bulk_create`, `bulk_update`, and a single queryset `delete()` call, to correctly and efficiently update all fields of all employees for the filtered Company, using `name` to match properly.

## Argument Reference

`def bulk_sync(new_models, key_fields, filters, batch_size=None, fields=None, skip_creates=False, skip_updates=False, skip_deletes=False):`
Combine bulk create, update, and delete. Make the DB match a set of in-memory objects.

-   `new_models`: An iterable of Django ORM `Model` objects that you want stored in the database. They may or may not have `id` set, but you should not have already called `save()` on them.
-   `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows. If a foreign key is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`. Use `['pk']` if you know the PKs already and want to use them to identify and match up `new_models` with existing database rows.
-   `filters`: Q() filters specifying the subset of the database to work in. Use `None` or `[]` if you want to sync against the entire table.
-   `batch_size`: (optional) passes through to Django `bulk_create.batch_size` and `bulk_update.batch_size`, and controls how many objects are created/updated per SQL query.
-   `fields`: (optional) List of fields to update. If not set, will sync all fields that are editable and not auto-created.
-   `exclude_fields`: (optional) list of fields to exclude from updates. Subtracts from the passed-in `fields` or default-calculated `fields` (see `fields` documentation above).
-   `exclude_fields`: (optional) List of fields to exclude from updates.
-   `skip_creates`: (optional) If truthy, will not perform any object creations needed to fully sync. Defaults to not skip.
-   `skip_updates`: (optional) If truthy, will not perform any object updates needed to fully sync. Defaults to not skip.
-   `skip_deletes`: (optional) If truthy, will not perform any object deletions needed to fully sync. Defaults to not skip.
-   `db_class`: (optional) Model class to operate on. If new_models always contains at least one object, this can be set automatically so is optional.
-   `select_for_update_of`: (optional) Iterable passed directly to select_for_update `of` clause to control locking of related models.
            See https://docs.djangoproject.com/en/dev/ref/models/querysets/#select-for-update for more information.

-   Returns a dict:
    ```
    {
    'stats': {
        "created": number of `new_models` not found in database and so created,
        "updated": number of `new_models` that were found in database as matched by `key_fields`,
        "deleted": number of deleted objects - rows in database that matched `filters` but were not present in `new_models`.
        }
    }
    ```

`def bulk_compare(old_models, new_models, key_fields, ignore_fields=None):`
Compare two sets of models by `key_fields`.

-   `old_models`: Iterable of Django ORM objects to compare.
-   `new_models`: Iterable of Django ORM objects to compare.
-   `key_fields`: Identifying attribute name(s) to match up `new_models` items with database rows. If a foreign key
    is being used as a key field, be sure to pass the `fieldname_id` rather than the `fieldname`.
-   `ignore_fields`: (optional) If set, provide field names that should not be considered when comparing objects.
-   Returns dict:
    ```
        {
            'added': list of all added objects.
            'unchanged': list of all unchanged objects.
            'updated': list of all updated objects.
            'updated_details': dict of {obj: {field_name: (old_value, new_value)}} for all changed fields in each updated object.
            'removed': list of all removed objects.
        }
    ```

## Frameworks Supported

This library is tested using Python 3 against Django 2.2+. If you are looking for versions that work with Django < 2.2,
please use the 1.x releases.
