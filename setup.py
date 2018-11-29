import setuptools

with open("README.md", 'r') as f:
    long_description = f.read()

setuptools.setup(
    name="phpbridge",
    version="0.0.3",
    author="Jan Verbeek",
    author_email="jan.verbeek@posteo.nl",
    description="Import PHP code into Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/blyxxyz/Python-PHP-Bridge",
    packages=setuptools.find_packages(),
    package_data={
        'phpbridge': ['*.php', '*/*.php', '*/*/*.php', '*/*/*/*.php'],
    },
    license="ISC",
    classifiers=[
        "Programming Language :: PHP",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: ISC License (ISCL)",
    ]
)
