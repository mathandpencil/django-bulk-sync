# Changelog

## [Unreleased]

## [3.3.0] - 2022-03-22
-   Force select_for_update order to prevent deadlocks. Many thanks to [@jpulec](https://github.com/jpulec) for pointing this out in #29.
-   Support passing `of` argument to internal select_for_update. Can be useful in working around "SELECT FOR UPDATE cannot be applied to the nullable side of an outer join".  Pull request #27, thanks [@osroca](https://github.com/osroca)!

## [3.2.0] - 2020-11-24
-   Support nonstandard `pk` fields. #25.
-   Use to_python to make sure keys are correct type. #22.

## [3.1.0] - 2020-08-28

### Added

-   Added support for manually specifying model to act on if new_models is empty. #11.
-   Added exclude_fields argument. Issue #15, pull request #16 from [@VKFisher](https://github.com/VKFisher).

## [3.0.1] - 2020-08-05

### Updated

-   Transactions now support models routed to different databases.

## [3.0.0] - 2020-07-28

### Changed

-   **Potentially breaking change** Retain PK if provided and ensure a crash if it mismatches on key_field. #10

    If your input models have the PK set already and expect it to be cleared by bulk_sync, that won't happen anymore.
    Please clear the pks yourself if you want them to seem like "new" objects.

## [2.1.0] - 2020-06-05

### Added

-   Added support for skip_deletes, skip_creates, and skip_updates in bulk_sync method. #9, pull request from [@mikefreemanwd](https://github.com/mikefreemanwd).

### Updated

-   Updated stats returned by bulk_sync to reflect what actually happened given the flags rather than what would have happend if all flags are false.

## [2.0.0] - 2020-05-19

### Removed

-   Removed support for Django versions before 2.2. Please use 1.x series for Django < 2.2.

[unreleased]: https://github.com/mathandpencil/django-bulk-sync/compare/v3.1.0..HEAD
[3.1.0]: https://github.com/mathandpencil/django-bulk-sync/compare/v3.0.1..v3.1.0
[3.0.1]: https://github.com/mathandpencil/django-bulk-sync/compare/v3.0.0..v3.0.1
[3.0.0]: https://github.com/mathandpencil/django-bulk-sync/compare/v2.1.0..v3.0.0
[2.1.0]: https://github.com/mathandpencil/django-bulk-sync/compare/v2.0.0..v2.1.0
[2.0.0]: https://github.com/mathandpencil/django-bulk-sync/releases/tag/v2.0.0
