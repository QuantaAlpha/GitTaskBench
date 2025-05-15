from setuptools import setup, find_packages

setup(
    name="gittaskbench",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyyaml>=6.0",
        "colorlog>=6.7.0",
        "numpy",
        "Levenshtein",
    ],
    entry_points={
        "console_scripts": [
            "gittaskbench=gittaskbench.cli:main",
        ],
    },
    author="GitTaskBench Team",
    author_email="example@example.com",
    description="A benchmarking tool for agent tasks",
    keywords="benchmark, evaluation, agent",
    python_requires=">=3.7",
)