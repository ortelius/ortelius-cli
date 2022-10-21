# Ortelius CLI

The dh Python script interacts with the Ortelius REST APIs to perform:

- Deploy the application to the environment
- Approve the application version
- Move the application version using the supplied task
- Create/replace the component version for the application version
- Assign a component version to an application version
- Assign the key/values pairs to the component version
- Create a bash file from the component toml file
- Export a domain including all objects to stdout
- Imports the export file into the new domain

## Installation

1. [Install Python 3.8 or newer](https://www.python.org/downloads/)
2. Install Ortelius CLI

   `pip install --upgrade ortelius-cli`

## Further Reading

See [Ortelius CLI Documentation](doc/dh.md) and [Ortelius Python API Documentation](doc/deployhub.md)
