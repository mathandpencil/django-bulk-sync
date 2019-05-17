from django.conf import settings
from django.db.models import Q
from django.test import TestCase

from bulk_sync import bulk_sync
from .models import Company, Employee


class BulkSyncTests(TestCase):

    def setUp(self):
        pass

    def test_all_features_at_once(self):
        c1 = Company.objects.create(name="Foo Products, Ltd.")
        c2 = Company.objects.create(name="Bar Microcontrollers, Inc.")

        e1 = Employee.objects.create(name="Scott", age=40, company=c1)
        e2 = Employee.objects.create(name="Isaac", age=9, company=c1)
        e3 = Employee.objects.create(name="Zoe", age=9, company=c1)
        e4 = Employee.objects.create(name="Bob", age=25, company=c2)

        # We should update Scott's and Isaac's age, delete Zoe, add Newguy and
        # add a second Bob (since he's not in company c1, which we filtered on.)
        new_objs = [
            Employee(name="Scott", age=41, company=c1),
            Employee(name="Isaac", age=9, company=c1),
            Employee(name="Newguy", age=10, company=c1),
            Employee(name="Bob", age=50, company=c1),
        ]

        ret = bulk_sync(
            new_models=new_objs,
            filters=Q(company_id=c1.id),
            key_fields=('name', ))

        self.assertEqual(2, ret['stats']['updated'])
        self.assertEqual(2, ret['stats']['created'])
        self.assertEqual(1, ret['stats']['deleted'])

        self.assertEqual(4, Employee.objects.filter(company=c1).count())
        self.assertEqual(1, Employee.objects.filter(company=c2).count())

        new_e1 = Employee.objects.get(id=e1.id)
        self.assertEqual("Scott", new_e1.name)
        self.assertEqual(41, new_e1.age)
        self.assertEqual(c1, new_e1.company)

        new_e2 = Employee.objects.get(id=e2.id)
        self.assertEqual("Isaac", new_e2.name)
        self.assertEqual(9, new_e2.age)
        self.assertEqual(c1, new_e2.company)

        with self.assertRaises(Employee.DoesNotExist):
            Employee.objects.get(id=e3.id)

        new_e4 = Employee.objects.get(id=e4.id)
        self.assertEqual("Bob", new_e4.name)
        self.assertEqual(25, new_e4.age)
        self.assertEqual(c2, new_e4.company)

        new_e3 = Employee.objects.get(name="Newguy")
        self.assertEqual("Newguy", new_e3.name)
        self.assertEqual(10, new_e3.age)
        self.assertEqual(c1, new_e3.company)

        new_e5 = Employee.objects.get(name="Bob", company=c1)
        self.assertEqual("Bob", new_e5.name)
        self.assertEqual(50, new_e5.age)
        self.assertEqual(c1, new_e5.company)
