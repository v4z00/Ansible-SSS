[English](README.md) · [Deutsch](README.de.md)

# Ansible-SSS

Mit diesem Werkzeug können Vertrauenspersonen einen Zugang gemeinsam wiederherstellen. Jede Person erhält einen eigenen Brief. Wie viele Briefe für das Vaultwarden-Master-Passwort oder den getrennten Infrastrukturzugang nötig sind, legst du selbst fest. Der Master-Satz kann außerdem einen TOTP-Einrichtungsschlüssel oder 2FA-Wiederherstellungscode enthalten.

## Wie eine Wiederherstellung abläuft

Beim Beispiel mit zwei von drei Anteilen treffen sich zwei der drei benannten Vertrauenspersonen mit ihren Briefen an einem Offline-Rechner. Sie öffnen die Wiederherstellungsseite, wählen dieselbe Kategorie und geben je einen Anteil aus ihrem Brief ein. Das Werkzeug prüft, ob die Anteile zum selben Satz gehören, und verifiziert das Ergebnis. Ein einzelner Brief reicht in diesem Beispiel nicht.

Der [Schnellstart](guides/START-HIER.md) ist für die Personen, die die Briefe öffnen. Die [Bedienungsanleitung](guides/BEDIENUNGSANLEITUNG.md) erklärt die Prüfung und Verwendung des Ergebnisses. Vor der Verteilung legt die Administration mit den [Vorlagen](examples/) das Quorum und die Empfänger fest.

**Staging s0.1.2** ergänzt dieses Beispiel. Vorhandene Briefe und Offline-Werkzeuge bleiben verwendbar.

## Auf Debian einrichten

Die stabile Version auf dem Rechner holen, der die Briefe erzeugen soll:

```bash
git clone --branch main https://github.com/v4z00/Ansible-SSS.git
cd Ansible-SSS
sudo install -d -m 0700 /root/sss-config
sudo test -e /root/sss-config/config.yml || sudo install -m 0600 examples/config.yml.example /root/sss-config/config.yml
sudo test -e /root/sss-config/trustees.yml || sudo install -m 0600 examples/trustees.yml.example /root/sss-config/trustees.yml
sudoedit /root/sss-config/config.yml /root/sss-config/trustees.yml
```

Die beiden `install -m`-Befehle sind für die Ersteinrichtung. **Bei einem bestehenden System die privaten Originaldateien behalten.** Zur Migration die vorhandene Konfiguration und bisherige `treuhaender.yml` lokal an die beiden angegebenen Ziele kopieren (Eigentümer root, Modus 0600). Deutsche Feldnamen, bereits installierte Generator-Konfigurationen und vorhandene SSS1-/SSS2-Briefe bleiben lesbar.

Trag Kontakt, Aufbewahrungsorte und Freigabeanlässe ein. Vergib pro Bereich jede Nummer von 1 bis `shares` genau einmal. `false` heißt, die Person erhält in diesem Bereich keinen Teil. Die Beispiele beginnen jeweils mit 2 von 3. Erlaubt sind 2 bis 20 Teile und höchstens 1.000 mögliche Kombinationen je Bereich. Wähle `language: de` oder `en` und bestätige mit `confirmed: true`.

```bash
bash run.sh
bash start-generator.sh --validate
bash start-generator.sh
```

Das Setup installiert bei Bedarf Ansible, Python und `ssss` und richtet `/root/rescue/SSS` lokal ein. Erzeuge die Briefe in einem privaten Terminal. Der Generator prüft jede zulässige Kombination und legt pro Lauf einen neuen Ordner unter `/root/rescue/SSS/ausgaben` an. Jede Person erhält nur ihren eigenen Brief. Für englische Briefe bei einem einzelnen Lauf genügt `bash start-generator.sh --lang en`.

## Im Notfall

Bereite den unabhängigen Wiederherstellungsrechner vorab vor. Vertrauenspersonen benötigen den gesamten Ordner `/root/rescue/SSS/offline` und die dokumentierte Tresorkopie. Browser und Terminal lesen die erforderliche Anzahl aus dem ersten Teil. Prüft zur Abnahme Master-, Infrastruktur- und gegebenenfalls den separaten KDBX-Zugang. Alte Teile bleiben nach einem neuen Lauf gültig, solange sich die Zugangsdaten nicht ändern. [Schnellstart](guides/START-HIER.md) · [Bedienungsanleitung](guides/BEDIENUNGSANLEITUNG.md)

## Als Add-on einsetzen

Auf einem Controller mit Allgm ab Version 0.8.1 ergänzt du die beiden Zeilen in der vorhandenen lokalen `versions.txt`. Behalte die übrigen Module und das leere Token-Feld am Ende der Zeile bei.

```text
# addon=SSS
SSS|0.0.0|https://github.com/v4z00/Ansible-SSS.git|
```

Prüfe die Vorschau im Controller-Ordner. Übernimm die stabile Version, wenn die Änderungen passen:

```bash
bin/control update-check --remote
bin/control update-check --apply
bin/control module-versions
bin/control sss --help
```

Das Update umfasst alle registrierten Module und installiert das Paket unter `playbooks/security/sss`. Der neue Befehl zeigt die Optionen für die Einrichtung. Die Briefe erzeugst du separat vor Ort. Private Einstellungen gehören nach `/root/sss-config`. Der eigenständige Weg oben funktioniert auch ohne Controller.

Entwicklungsbranch ist `staging`. Die Testbefehle stehen in der [englischen README](README.md#development). Der Code ist mit KI-Unterstützung entstanden. Hinweise aus der Praxis sind willkommen. Bitte ausschließlich Beispieldaten in Issues posten. [MIT-Lizenz](LICENSE)
