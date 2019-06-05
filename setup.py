import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="django-bulk-sync",
    version='1.2.0',
    description="Combine bulk add, update, and delete into a single call.",
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/mathandpencil/django-bulk-sync",
    author="Scott Stafford",
    author_email="scott.stafford+bulksync@gmail.com",
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: Django',
    ],
    zip_safe=False,
)
