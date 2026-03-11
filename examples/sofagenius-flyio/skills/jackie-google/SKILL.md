---
name: jackie-google
description: Access Google Workspace — Drive (list/read/upload files), Sheets (read/write data), Docs (read content), and Contacts (search/list). Uses Google REST APIs with service account auth.
metadata:
  {
    "openclaw":
      {
        "emoji": "🔧",
        "requires": { "anyBins": ["python3", "python"], "env": ["GOOGLE_WORKSPACE_CREDENTIALS"] },
      },
  }
---

# Jackie Google Workspace

Access Google Drive, Sheets, Docs, and Contacts without opening a browser. Uses the same service account auth pattern as jackie-calendar.

## Setup

Requires `GOOGLE_WORKSPACE_CREDENTIALS` env var with a service account JSON that has domain-wide delegation enabled. The service account must be granted scopes for Drive, Sheets, Docs, and Contacts. Set `GOOGLE_DELEGATED_USER` to the email address to impersonate (e.g. `lily@example.com`).

## When to use

- User wants to find or read a file on Google Drive
- User wants to read/write data in a Google Sheet
- User wants to read a Google Doc
- User wants to look up a contact

---

## Google Drive

### List files

```bash
python3 {baseDir}/scripts/bridge.py drive_list --query "name contains 'roadmap'" --count 10
```

Lists files matching a Drive search query. Uses [Drive search syntax](https://developers.google.com/drive/api/guides/search-files). Without `--query`, lists recent files.

### Read a file

```bash
python3 {baseDir}/scripts/bridge.py drive_read --file-id "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
```

Reads the content of a file. For Google Docs/Sheets, exports as plain text. For other files, downloads if under 1MB.

### Upload a file

```bash
python3 {baseDir}/scripts/bridge.py drive_upload --name "report.md" --content "# Q1 Report\n\n..." --mime-type "text/markdown"
```

Uploads a new file to Drive. Optional `--folder-id` to specify destination folder.

---

## Google Sheets

### Read a sheet

```bash
python3 {baseDir}/scripts/bridge.py sheets_read --spreadsheet-id "1BxiMVs..." --range "Sheet1!A1:D20"
```

Reads cell values from a spreadsheet range.

### Write to a sheet

```bash
python3 {baseDir}/scripts/bridge.py sheets_write --spreadsheet-id "1BxiMVs..." --range "Sheet1!A1" --values '[["Name","Score"],["Alice",95]]'
```

Writes values to a spreadsheet range. `--values` is a JSON array of arrays.

### Append to a sheet

```bash
python3 {baseDir}/scripts/bridge.py sheets_append --spreadsheet-id "1BxiMVs..." --range "Sheet1!A1" --values '[["Bob",88]]'
```

Appends rows after the last row with data.

---

## Google Docs

### Read a doc

```bash
python3 {baseDir}/scripts/bridge.py docs_read --doc-id "1BxiMVs..."
```

Reads the plain text content of a Google Doc.

---

## Google Contacts

### Search contacts

```bash
python3 {baseDir}/scripts/bridge.py contacts_search --query "alice" --count 10
```

Searches contacts by name or email.

### List contacts

```bash
python3 {baseDir}/scripts/bridge.py contacts_list --count 20
```

Lists contacts sorted by last updated.
