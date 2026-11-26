# Local emergency recovery kit

Run `bin/control sss --help` for the available setup options. Prepare the private files under `/root/sss-config` using the add-on examples. Run `bin/control sss --check` to preview setup, then `bin/control sss --setup` to install the recovery tools on this controller. Generate letters separately in a private terminal.

The default command displays usage. The setup playbook targets localhost. Recovery instructions in English and German are installed with the offline tools.

```json
{
  "schema_version": 1,
  "kind": "command",
  "ref": "sss",
  "title": "Prepare the local emergency recovery kit",
  "documented": true,
  "fields": [],
  "constraints": [],
  "sources": [
    "bin/control.d/sss.json",
    "bin/control.d/sss.sh",
    "playbooks/security/sss/run.sh",
    "playbooks/security/sss/setup.yml"
  ],
  "source_hashes": {
    "bin/control.d/sss.json": "a2846881f64d848aaebde5108978c7ac54559e57b563cc802b397687b467402d",
    "bin/control.d/sss.sh": "e396fbceeba69b6a4d4a00ba73f9b7e7bedb78736fb6326218cde008dab2b11e",
    "playbooks/security/sss/run.sh": "8881a2eb68be52e83f991b72398c567606f74cafa6e73673c2822589c6a5375b",
    "playbooks/security/sss/setup.yml": "1dcb105ead585f795fd929dc7c0033e06b7ddd34180eae09f9cdd3c31a33502f"
  }
}
```
