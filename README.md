# aws-ec2-to-rdg-pipeline

Jenkins pipeline that generates Remote Desktop Connection Manager (.rdg) files for EC2 instances across AWS accounts.

## Background

Connecting to Windows servers across dozens of customer stacks meant looking up public IPs in the AWS console and keeping personal connection lists up to date by hand. Every stack rebuild or IP change made those lists stale.

This started as a local Python script written to generate a ready-to-use RDCMan (Remote Desktop Connection Manager) file straight from AWS. It was then adopted into the team's production automation as a self-service Jenkins pipeline, so anyone can download an up-to-date connection file for any environment in a few clicks.

> The code in this repo has been sanitized and generalized from production work. Names, tags, and internal references have been replaced, so it is meant to show the approach rather than run as a drop-in tool.

## Repository layout

```
aws-ec2-to-rdg-pipeline/
├── Jenkinsfile       # Parameters, role assumption, and artifact download
└── ec2_to_rdg.py     # Python (boto3) logic that builds the .rdg file
```

## How it works

1. The user picks an **environment** (prod, qa, or uat) and a **region**.
2. Jenkins looks up that environment's deployment role and account from `config/env_parameters.yml` and assumes it with `withAWS`.
3. The script finds every **running Windows instance with a public IP** whose Name tag matches the application's server roles (`appserver`, `processing`, `gisserver`, `webportal`).
4. Servers are grouped into folders by **stack**, and each folder is labeled with the stack's `Customer` tag, for example `prod-12 (CustomerName)`.
5. The `.rdg` file is written and archived as a **Jenkins build artifact** for the user to download and open in RDCMan.

## Improvements made for production

When the script moved into the shared pipeline, it was cleaned up and extended:

- **Grouped by customer stack.** Connections are organized into one folder per stack instead of a single flat list, which makes finding the right server much faster.
- **More accurate results.** Only servers matching the application's role patterns are included, which filters out unrelated demo and utility servers that previously appeared.
- **Safe file generation.** The file is built with Python's XML library, so special characters in server names or tags are escaped properly and can't produce a corrupted or unopenable file.
- **Single source of truth.** The role patterns are defined once and combined with the selected environment at runtime, replacing three duplicated per-environment lists.
- **Timestamped output.** Each file is named `<environment>_<region>_<timestamp>.rdg`, so downloads never overwrite each other.

## Design notes

- **Read-only.** The pipeline only describes instances and never changes anything in AWS.
- **Clean handoff to Jenkins.** The script prints a `---SPLIT---` marker before the output filename, so the Jenkinsfile can show the console output and archive the correct file.
- **Optional customer filter.** The `CUSTOMER` setting in the script is empty by default (all customers), but it can limit the file to a single customer's servers.

## Testing

- Verified across all accounts and regions, confirming the generated files open correctly in RDCMan with the expected stack and customer grouping.

## Notes

- `config/env_parameters.yml` stands in for an internal configuration file that maps each environment and region to its deployment IAM role and AWS account.
- `REPO_BRANCH` is used by the Jenkins job's SCM configuration to run the pipeline from `main` or a feature branch.

## Tech

Jenkins (declarative pipeline) · Python 3 · boto3 · AWS EC2, STS · RDCMan (XML)
