from django.conf import settings
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=140)


class Employee(models.Model):
    age = models.IntegerField()
    name = models.CharField(max_length=140, blank=True, null=True)

    company = models.ForeignKey(Company, models.CASCADE)

    def __str__(self):
        return "Employee: {} age {} company {}".format(self.name, self.age, self.company_id)

class EmployeeDifferentPk(models.Model):
    employee_id = models.AutoField(primary_key=True)

    age = models.IntegerField()
    name = models.CharField(max_length=140, blank=True, null=True)

    company = models.ForeignKey(Company, models.CASCADE)

    def __str__(self):
        return "EmployeeDiffPk: {} age {} company {}".format(self.name, self.age, self.company_id)


class EmployeeWithOffice(models.Model):
    age = models.IntegerField()
    name = models.CharField(max_length=140, blank=True, null=True)

    company = models.ForeignKey(Company, models.CASCADE)

    def __str__(self):
        return "EmployeeWithOffice: {} age {} company {}".format(self.name, self.age, self.company_id)

class Office(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    employees = models.ManyToManyField(
        "EmployeeWithOffice", through="EmployeeOffice",
    )

class EmployeeOffice(models.Model):
    office = models.ForeignKey(
        "Office", null=False, on_delete=models.CASCADE
    )
    employee = models.ForeignKey(
        "EmployeeWithOffice", null=True, on_delete=models.CASCADE
    )

    def __str__(self):
        return "EmployeeOffice: {} employee {} office {}".format(self.employee.name, self.office.id)
