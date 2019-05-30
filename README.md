# django-bulk-sync
Combine bulk add, update, and delete into a single call.

django-bulk-sync is a package to support the Django ORM, which synthesizes the concepts of bulk_create, bulk_update, and delete into a single call to `bulk_sync`.

## An example:

Companies have zero or more Employees. You want to efficiently sync the names of all employees for a single `Company` from an import from that company, but some are added, updated, or removed.  The simple approach is inefficient -- read the import line by line, and:

For each of N records:

- SELECT to check for the employee's existence
- UPDATE if it exists, INSERT if it doesn't

Then figure out some way to identify what was missing and delete it.  As is so often the case, the speed of this process is controlled mostly by the number of queries run, and here it is about two queries for every record, and so O(N).

Instead, with bulk_sync, we can avoid the O(N) number of queries, and simplify the logic we have to write as well:
	
```python
from django.db.models import Q

new_models = []
for line in company_import_file:
	# The `.id` (or `.pk`) field should not be set. Instead, `key_fields` 
	# tells it how to match.
	e = Employee(name=line['name'], phone_number=line['phone_number'], ...)
	new_models.append(e)

# `filters` controls the subset of objects considered when deciding to 
# update or delete.
filters = Q(company_id=501)  
# `key_fields` matches an existing object if all `key_fields` are equal.
key_fields = ('name', )  
ret = bulk_sync(
        new_models=new_models,
        filters=filters,
        key_fields=key_fields)

print("Results of bulk_sync: "
      "{created} created, {updated} updated, {deleted} deleted."
      		.format(**ret['stats']))
```

Under the hood, it will atomically call `bulk_create`, `bulk_update`, and a single queryset `delete()` call, to correctly and efficiently update all fields of all employees for the filtered Company, using `name` to match properly. 

## Installation and Quick Start

The package is available on pip as [django-bulk-sync][django-bulk-sync].  Run:

`pip install django-bulk-sync`

then import via:

`from bulk_sync import bulk_sync`

And use as in the example above.

