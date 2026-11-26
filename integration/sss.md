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
    "playbooks/security/sss/setup.yml": "55c6c224b2438ce1a9e8b3c9f2ef61b6af2c78e389b1f5cc460ef08e935acf46"
  },
  "i18n": {
    "de": {
      "title": "Lokale Notfallwiederherstellung vorbereiten",
      "description": "# Lokale Notfallwiederherstellung vorbereiten\n\nMit `bin/control sss --help` siehst du die verfügbaren Optionen. Erstelle die privaten Eingabedateien unter `/root/sss-config` anhand der Beispiele. Prüfe die Einrichtung mit `bin/control sss --check` und installiere die Werkzeuge anschließend mit `bin/control sss --setup`. Erzeuge die Briefe getrennt in einem privaten Terminal.\n\nOhne Option zeigt der Befehl seine Hilfe. Das Setup läuft auf localhost. Die Offline-Werkzeuge enthalten die Wiederherstellungsanleitungen auf Deutsch und Englisch.",
      "fields": {}
    },
    "en": {
      "title": "Prepare the local emergency recovery kit",
      "description": "# Local emergency recovery kit\n\nRun `bin/control sss --help` for the available setup options. Prepare the private files under `/root/sss-config` using the add-on examples. Run `bin/control sss --check` to preview setup, then `bin/control sss --setup` to install the recovery tools on this controller. Generate letters separately in a private terminal.\n\nThe default command displays usage. The setup playbook targets localhost. Recovery instructions in English and German are installed with the offline tools.",
      "fields": {}
    }
  }
}
```
