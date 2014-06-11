from setuptools import setup, find_packages

setup(
    name='django-emailmeld',
    version='0.0.1',
    description='Django Email Templater.',
    long_description = open( 'README.md', 'r').read() + open('AUTHORS.rst', 'r').read() + open('CHANGELOG.rst', 'r').read(),
    author='Thomas',
    author_email='spam@ionata.com.au',
    url='http://github.com/ionata/django-emailmeld',
    packages = find_packages(exclude=['project',]),
    install_requires = [
        'markdown'
    ],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: BSD License",
        "Development Status :: 4 - Beta",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    zip_safe=False,
)
