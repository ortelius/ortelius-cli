# Ortelius CLI

The dh Python script interacts with the Ortelius REST APIs to perform:

- Create/replace the _Component Version_ Version_ for the _Application Version_
- Assign a component version to an _Application Version_
- Assign the key/values pairs to the _Component Version_
- Create a bash file from the _Component_ .toml file
- Export a _Domain_ including all objects to stdout
- Imports the export file into the new _Domain_
- Deploy the _Application_
- Persist SBOMs to the  _Component Version_
- Persist SonarQube Project Status, Bugs, Code Smells, and Violations metrics to the  _Component Version_
- Persist Veracode Score to the  _Component Version_
- Persist License File to the  _Component Version_
- Persist Readme File the  _Component Version_
- Persist Swagger and OpenAPI files the  _Component Version_
- Persist Git Branch, Branch Create Commit, Branch Create Timestamp, Branch Parent, Commit, Commit Authors, Committers Count, Commit Timestamp, Lines Added, Lines Deleted, Lines Total, Org, Repo, Repo Project, Signed Off By, Tag, Url, Verified Commit

## Installation

1. [Install Python 3.8 or newer](https://www.python.org/downloads/)
2. Install Ortelius CLI

   `pip install --upgrade ortelius-cli`

## Further Reading

See [Ortelius CI/CD Integration](https://docs.ortelius.io/guides/userguide/integrations/ci-cd_integrations/) and [Ortelius Python API Documentation](doc/deployhub.md)
