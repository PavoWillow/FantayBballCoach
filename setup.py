from setuptools import setup, find_packages

setup(
    name="fantasy_basketball_gpt_advisor",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "espn-api",
        "nba-api",
        "cachetools",
        "openai",
        # Add other dependencies here
    ],
    description="A Python app to analyze fantasy basketball data using GPT",
    author="Patrick Loomis",
    license="MIT",
)