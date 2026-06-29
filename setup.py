from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-jumpserver",
    version="0.2.0",
    description="Stateful CLI harness for JumpServer bastion host",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="cli-anything",
    url="https://www.jumpserver.com",
    python_requires=">=3.11",
    install_requires=[
        "click>=8.0",
        "requests>=2.28",
        "pyyaml>=6.0",
        "websocket-client>=1.5",
    ],
    packages=find_namespace_packages(include=["cli_anything.*"]),
    namespace_packages=["cli_anything"],
    entry_points={
        "console_scripts": [
            "cli-anything-jumpserver=cli_anything.jumpserver.jumpserver_cli:cli_main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: Security",
    ],
    keywords="jumpserver bastion pam cli security",
)
