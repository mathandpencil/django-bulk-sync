from setuptools import setup

setup(
    name="django-bulk-sync",
    version='1.1.0',
    description="Combine bulk add, update, and delete into a single call.",
    long_description=open("README.md").read(),
    long_description_content_type='text/markdown',
    url="https://github.com/mathandpencil/django-bulk-sync",
    author="Scott Stafford",
    author_email="scott.stafford+bulksync@gmail.com",
    packages=[
        "bulk_sync",
    ],
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Django',
    ],
    zip_safe=False,
)
