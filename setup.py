import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="py-wallabag",
    version="0.0.4",
    description="Python wrapper for the Wallabag Rest API",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/zeroone2numeral2/py-wallabag",
    author="zeroone2numeral2",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=["wallabag"],
    include_package_data=True,
    install_requires=["requests", "pytz"],
    # entry_points={
    #     "console_scripts": [
    #         "realpython=reader.__main__:main",
    #     ]
    # },
)
