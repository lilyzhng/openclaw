#!/usr/bin/env python3
"""Google Workspace bridge — Drive, Sheets, Docs, Contacts.

Uses urllib (stdlib) + google-auth for service account authentication.
Same auth pattern as jackie-calendar.

Usage:
    python3 bridge.py drive_list --query "name contains 'roadmap'" --count 10
    python3 bridge.py drive_read --file-id "1BxiMVs..."
    python3 bridge.py sheets_read --spreadsheet-id "1BxiMVs..." --range "Sheet1!A1:D20"
    python3 bridge.py contacts_search --query "alice"
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
try:
    import feedback_store as _fb
except ImportError:
    _fb = None

SKILL_NAME = "jackie-google"

DRIVE_API = "https://www.googleapis.com/drive/v3"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
DOCS_API = "https://docs.googleapis.com/v1/documents"
PEOPLE_API = "https://people.googleapis.com/v1"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/contacts.readonly",
]


def _log(action, args, result, success, start, error=None):
    duration = round((time.monotonic() - start) * 1000)
    if _fb:
        _fb.log_execution(SKILL_NAME, action, args, result, success, duration, error)


def _get_access_token() -> str:
    """Get access token via service account with domain-wide delegation."""
    creds_json = os.environ.get("GOOGLE_WORKSPACE_CREDENTIALS") or os.environ.get("GOOGLE_CALENDAR_CREDENTIALS")
    if not creds_json:
        print(json.dumps({"error": "GOOGLE_WORKSPACE_CREDENTIALS env var is not set."}))
        sys.exit(1)

    from google.oauth2 import service_account
    from google.auth.transport import requests as google_requests

    creds_info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(
        creds_info, scopes=SCOPES,
    )

    # If delegated user is set, impersonate them (required for Contacts, optional for Drive/Sheets)
    delegated_user = os.environ.get("GOOGLE_DELEGATED_USER")
    if delegated_user:
        credentials = credentials.with_subject(delegated_user)

    credentials.refresh(google_requests.Request())
    return credentials.token


def _api_get(url: str, token: str) -> dict | list | bytes:
    """GET from a Google API."""
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()
        if "application/json" in content_type:
            return json.loads(raw.decode())
        return raw


def _api_post(url: str, token: str, body: dict) -> dict:
    """POST to a Google API."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _api_put(url: str, token: str, body: dict) -> dict:
    """PUT to a Google API."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="PUT", headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


# --- Google Drive ---

def drive_list(query: str | None, count: int) -> None:
    action_args = {"query": query, "count": count}
    start = time.monotonic()
    try:
        token = _get_access_token()
        params = {
            "pageSize": str(count),
            "orderBy": "modifiedTime desc",
            "fields": "files(id,name,mimeType,modifiedTime,size,webViewLink,owners)",
        }
        if query:
            params["q"] = query

        qs = urllib.parse.urlencode(params)
        resp = _api_get(f"{DRIVE_API}/files?{qs}", token)

        files = []
        for f in resp.get("files", []):
            files.append({
                "id": f["id"],
                "name": f["name"],
                "mimeType": f["mimeType"],
                "modifiedTime": f.get("modifiedTime"),
                "size": f.get("size"),
                "url": f.get("webViewLink", ""),
                "owner": f.get("owners", [{}])[0].get("displayName") if f.get("owners") else None,
            })

        result = {"action": "drive_list", "count": len(files), "files": files}
        print(json.dumps(result, indent=2))
        _log("drive_list", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Drive API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("drive_list", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("drive_list", action_args, result, False, start, str(e))


def drive_read(file_id: str) -> None:
    action_args = {"file_id": file_id}
    start = time.monotonic()
    try:
        token = _get_access_token()

        # First get file metadata to determine type
        meta = _api_get(f"{DRIVE_API}/files/{file_id}?fields=id,name,mimeType,size", token)
        mime = meta.get("mimeType", "")
        name = meta.get("name", "")

        content = ""
        if mime == "application/vnd.google-apps.document":
            # Export Google Doc as plain text
            raw = _api_get(f"{DRIVE_API}/files/{file_id}/export?mimeType=text/plain", token)
            content = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        elif mime == "application/vnd.google-apps.spreadsheet":
            # Export Google Sheet as CSV
            raw = _api_get(f"{DRIVE_API}/files/{file_id}/export?mimeType=text/csv", token)
            content = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        elif mime == "application/vnd.google-apps.presentation":
            # Export Google Slides as plain text
            raw = _api_get(f"{DRIVE_API}/files/{file_id}/export?mimeType=text/plain", token)
            content = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
        else:
            # Regular file — download if under 1MB
            size = int(meta.get("size", 0))
            if size > 1_000_000:
                content = f"(file too large: {size} bytes, max 1MB for direct read)"
            else:
                raw = _api_get(f"{DRIVE_API}/files/{file_id}?alt=media", token)
                if isinstance(raw, bytes):
                    try:
                        content = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        content = f"(binary file, {len(raw)} bytes)"
                else:
                    content = str(raw)

        # Truncate very long content
        if len(content) > 10000:
            content = content[:10000] + "\n... (truncated)"

        result = {
            "action": "drive_read",
            "file_id": file_id,
            "name": name,
            "mimeType": mime,
            "content": content,
        }
        print(json.dumps(result, indent=2))
        _log("drive_read", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Drive API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("drive_read", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("drive_read", action_args, result, False, start, str(e))


def drive_upload(name: str, content: str, mime_type: str, folder_id: str | None) -> None:
    action_args = {"name": name, "mime_type": mime_type, "folder_id": folder_id}
    start = time.monotonic()
    try:
        token = _get_access_token()

        # Multipart upload: metadata + content
        metadata = {"name": name, "mimeType": mime_type}
        if folder_id:
            metadata["parents"] = [folder_id]

        boundary = "----JackieUploadBoundary"
        body_parts = [
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{json.dumps(metadata)}\r\n",
            f"--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n{content}\r\n",
            f"--{boundary}--",
        ]
        body_data = "".join(body_parts).encode()

        req = urllib.request.Request(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            data=body_data,
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode())

        result = {
            "action": "drive_upload",
            "file_id": resp_data.get("id", ""),
            "name": name,
            "mimeType": resp_data.get("mimeType", ""),
            "url": f"https://drive.google.com/file/d/{resp_data.get('id', '')}/view",
        }
        print(json.dumps(result, indent=2))
        _log("drive_upload", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Drive API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("drive_upload", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("drive_upload", action_args, result, False, start, str(e))


# --- Google Sheets ---

def sheets_read(spreadsheet_id: str, range_: str) -> None:
    action_args = {"spreadsheet_id": spreadsheet_id, "range": range_}
    start = time.monotonic()
    try:
        token = _get_access_token()
        encoded_range = urllib.parse.quote(range_)
        resp = _api_get(f"{SHEETS_API}/{spreadsheet_id}/values/{encoded_range}", token)

        result = {
            "action": "sheets_read",
            "spreadsheet_id": spreadsheet_id,
            "range": resp.get("range", range_),
            "values": resp.get("values", []),
            "rows": len(resp.get("values", [])),
        }
        print(json.dumps(result, indent=2))
        _log("sheets_read", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Sheets API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("sheets_read", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("sheets_read", action_args, result, False, start, str(e))


def sheets_write(spreadsheet_id: str, range_: str, values: list) -> None:
    action_args = {"spreadsheet_id": spreadsheet_id, "range": range_}
    start = time.monotonic()
    try:
        token = _get_access_token()
        encoded_range = urllib.parse.quote(range_)
        body = {
            "range": range_,
            "majorDimension": "ROWS",
            "values": values,
        }
        resp = _api_put(
            f"{SHEETS_API}/{spreadsheet_id}/values/{encoded_range}?valueInputOption=USER_ENTERED",
            token, body,
        )

        result = {
            "action": "sheets_write",
            "spreadsheet_id": spreadsheet_id,
            "updated_range": resp.get("updatedRange", ""),
            "updated_rows": resp.get("updatedRows", 0),
            "updated_cells": resp.get("updatedCells", 0),
        }
        print(json.dumps(result, indent=2))
        _log("sheets_write", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Sheets API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("sheets_write", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("sheets_write", action_args, result, False, start, str(e))


def sheets_append(spreadsheet_id: str, range_: str, values: list) -> None:
    action_args = {"spreadsheet_id": spreadsheet_id, "range": range_}
    start = time.monotonic()
    try:
        token = _get_access_token()
        encoded_range = urllib.parse.quote(range_)
        body = {
            "range": range_,
            "majorDimension": "ROWS",
            "values": values,
        }
        resp = _api_post(
            f"{SHEETS_API}/{spreadsheet_id}/values/{encoded_range}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS",
            token, body,
        )

        updates = resp.get("updates", {})
        result = {
            "action": "sheets_append",
            "spreadsheet_id": spreadsheet_id,
            "updated_range": updates.get("updatedRange", ""),
            "updated_rows": updates.get("updatedRows", 0),
        }
        print(json.dumps(result, indent=2))
        _log("sheets_append", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Sheets API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("sheets_append", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("sheets_append", action_args, result, False, start, str(e))


# --- Google Docs ---

def docs_read(doc_id: str) -> None:
    action_args = {"doc_id": doc_id}
    start = time.monotonic()
    try:
        token = _get_access_token()
        resp = _api_get(f"{DOCS_API}/{doc_id}", token)

        # Extract plain text from the document body
        text_parts = []
        for element in resp.get("body", {}).get("content", []):
            paragraph = element.get("paragraph", {})
            for pe in paragraph.get("elements", []):
                text_run = pe.get("textRun", {})
                if text_run.get("content"):
                    text_parts.append(text_run["content"])

        content = "".join(text_parts)
        if len(content) > 10000:
            content = content[:10000] + "\n... (truncated)"

        result = {
            "action": "docs_read",
            "doc_id": doc_id,
            "title": resp.get("title", ""),
            "content": content,
        }
        print(json.dumps(result, indent=2))
        _log("docs_read", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"Docs API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("docs_read", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("docs_read", action_args, result, False, start, str(e))


# --- Google Contacts ---

def contacts_search(query: str, count: int) -> None:
    action_args = {"query": query, "count": count}
    start = time.monotonic()
    try:
        token = _get_access_token()
        params = urllib.parse.urlencode({
            "query": query,
            "readMask": "names,emailAddresses,phoneNumbers,organizations",
            "pageSize": str(count),
        })
        resp = _api_get(f"{PEOPLE_API}/people:searchContacts?{params}", token)

        contacts = []
        for item in resp.get("results", []):
            person = item.get("person", {})
            contacts.append(_format_contact(person))

        result = {"action": "contacts_search", "query": query, "count": len(contacts), "contacts": contacts}
        print(json.dumps(result, indent=2))
        _log("contacts_search", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"People API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("contacts_search", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("contacts_search", action_args, result, False, start, str(e))


def contacts_list(count: int) -> None:
    action_args = {"count": count}
    start = time.monotonic()
    try:
        token = _get_access_token()
        params = urllib.parse.urlencode({
            "resourceName": "people/me",
            "personFields": "names,emailAddresses,phoneNumbers,organizations",
            "pageSize": str(count),
            "sortOrder": "LAST_MODIFIED_DESCENDING",
        })
        resp = _api_get(f"{PEOPLE_API}/people/me/connections?{params}", token)

        contacts = []
        for person in resp.get("connections", []):
            contacts.append(_format_contact(person))

        result = {"action": "contacts_list", "count": len(contacts), "contacts": contacts}
        print(json.dumps(result, indent=2))
        _log("contacts_list", action_args, result, True, start)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if hasattr(e, "read") else ""
        result = {"error": f"People API error: {e.code} {e.reason}", "details": error_body}
        print(json.dumps(result, indent=2))
        _log("contacts_list", action_args, result, False, start, str(e))
    except Exception as e:
        result = {"error": str(e)}
        print(json.dumps(result, indent=2))
        _log("contacts_list", action_args, result, False, start, str(e))


def _format_contact(person: dict) -> dict:
    """Extract key fields from a People API person resource."""
    names = person.get("names", [])
    emails = person.get("emailAddresses", [])
    phones = person.get("phoneNumbers", [])
    orgs = person.get("organizations", [])
    return {
        "name": names[0].get("displayName", "") if names else "",
        "emails": [e.get("value", "") for e in emails],
        "phones": [p.get("value", "") for p in phones],
        "organization": orgs[0].get("name", "") if orgs else "",
    }


# --- Main ---

def main() -> None:
    parser = argparse.ArgumentParser(description="Jackie Google Workspace Bridge")
    parser.add_argument("action", choices=[
        "drive_list", "drive_read", "drive_upload",
        "sheets_read", "sheets_write", "sheets_append",
        "docs_read",
        "contacts_search", "contacts_list",
    ])
    parser.add_argument("--query", help="Search query (drive_list, contacts_search)")
    parser.add_argument("--count", type=int, default=10, help="Number of items (default 10)")
    parser.add_argument("--file-id", dest="file_id", help="Drive file ID (drive_read)")
    parser.add_argument("--name", help="File name (drive_upload)")
    parser.add_argument("--content", help="File content (drive_upload)")
    parser.add_argument("--mime-type", dest="mime_type", default="text/plain", help="MIME type (drive_upload)")
    parser.add_argument("--folder-id", dest="folder_id", help="Drive folder ID (drive_upload)")
    parser.add_argument("--spreadsheet-id", dest="spreadsheet_id", help="Sheets spreadsheet ID")
    parser.add_argument("--range", dest="range_", help="Cell range like Sheet1!A1:D20")
    parser.add_argument("--values", help="JSON array of arrays for sheets_write/sheets_append")
    parser.add_argument("--doc-id", dest="doc_id", help="Google Doc ID (docs_read)")
    args = parser.parse_args()

    if args.action == "drive_list":
        drive_list(args.query, args.count)
    elif args.action == "drive_read":
        if not args.file_id:
            print(json.dumps({"error": "--file-id is required"}))
            sys.exit(1)
        drive_read(args.file_id)
    elif args.action == "drive_upload":
        if not args.name or not args.content:
            print(json.dumps({"error": "--name and --content are required"}))
            sys.exit(1)
        drive_upload(args.name, args.content, args.mime_type, args.folder_id)
    elif args.action == "sheets_read":
        if not args.spreadsheet_id or not args.range_:
            print(json.dumps({"error": "--spreadsheet-id and --range are required"}))
            sys.exit(1)
        sheets_read(args.spreadsheet_id, args.range_)
    elif args.action == "sheets_write":
        if not args.spreadsheet_id or not args.range_ or not args.values:
            print(json.dumps({"error": "--spreadsheet-id, --range, and --values are required"}))
            sys.exit(1)
        sheets_write(args.spreadsheet_id, args.range_, json.loads(args.values))
    elif args.action == "sheets_append":
        if not args.spreadsheet_id or not args.range_ or not args.values:
            print(json.dumps({"error": "--spreadsheet-id, --range, and --values are required"}))
            sys.exit(1)
        sheets_append(args.spreadsheet_id, args.range_, json.loads(args.values))
    elif args.action == "docs_read":
        if not args.doc_id:
            print(json.dumps({"error": "--doc-id is required"}))
            sys.exit(1)
        docs_read(args.doc_id)
    elif args.action == "contacts_search":
        if not args.query:
            print(json.dumps({"error": "--query is required"}))
            sys.exit(1)
        contacts_search(args.query, args.count)
    elif args.action == "contacts_list":
        contacts_list(args.count)


if __name__ == "__main__":
    main()
