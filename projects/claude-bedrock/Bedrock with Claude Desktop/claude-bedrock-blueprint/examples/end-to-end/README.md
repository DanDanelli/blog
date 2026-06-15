# End-to-end example

> **Status:** placeholder — lands after the Part 2 modules.

The one composition that wires the whole stack together so you can *see it run*: an AgentCore
Gateway + an OpenAPI/REST target + the REQUEST interceptor + the DCR bridge + identity +
observability, pointed at a public or stub downstream (so you don't need an enterprise tenant
to try it).

## How to run (once it lands)

```bash
cp terraform.example.tfvars terraform.tfvars   # fill in your own identifiers
terraform init
terraform apply
# ... exercise it, then:
terraform destroy
```

Everything environment-specific is a variable in `terraform.example.tfvars` — no source edits.
