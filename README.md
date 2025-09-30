# Ortelius CLI

This Go program is a replacement for the Python script.

> Note: The dh Python script interacts with the Ortelius REST APIs has been deprecated can can be found on the [maint branch](https://github.com/ortelius/ortelius-cli/tree/maint).

Ortelius CLI will:

- Create/replace the _Component Version_ Version_ for the _Application Version_
- Assign a component version to an _Application Version_
- Assign the key/values pairs to the _Component Version_
- Create a bash file from the _Component_ .toml file
- Export a _Domain_ including all objects to stdout
- Imports the export file into the new _Domain_
- Deploy the _Application_
- Record deployment of the _Application_
- Persist SBOMs to the  _Component Version_
- Persist SonarQube Project Status, Bugs, Code Smells, and Violations metrics to the  _Component Version_
- Persist Veracode Score to the  _Component Version_
- Persist License File to the  _Component Version_
- Persist Readme File the  _Component Version_
- Persist Swagger and OpenAPI files the  _Component Version_
- Persist Git Branch, Branch Create Commit, Branch Create Timestamp, Branch Parent, Commit, Commit Authors, Committers Count, Commit Timestamp, Lines Added, Lines Deleted, Lines Total, Org, Repo, Repo Project, Signed Off By, Tag, Url, Verified Commit

## Installation

1. Download from the [GitHub Releases](https://github.com/ortelius/ortelius-cli/releases) and add to your CI/CD Pipeline.
2. Configure a `component.toml` that is used to map the Git repo to an Ortelius _Component Version_ and _Application_.

   ```toml
   Domain = "GLOBAL.Open Source.Linux Foundation.CDF.Ortelius"

   Application = "${Domain}.dhcli-app"
   Application_Version = "v0.1.0"

   Name = "${Domain}.dhcli"
   Variant = "main"
   Version = "v1.0.0"
   ```

3. Add the CLI call `ortelius updatecomp <flags>` to your pipeline after the build and SBOM generation and before deployment.  This enables the Ortelius to gather details about the Git Repo and SBOM and persist it to the Ortelius database as a _Component Version_ for Vulnerability Analysis.

4. Add the CLI call `ortelius deploy <flag>` to your pipeline after deployment.  This enables Ortelius to map and _Application_ to a deployed environment, i.e. Prod, creating the digital twin of the application running in the environment.  This digital twin is used to report on **Post-Deployment Vulnerabilities in Real-time**.

## Further Reading

See [Ortelius CI/CD Integration](https://docs.ortelius.io/guides/userguide/integrations/ci-cd_integrations/).
