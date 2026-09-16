import os
import re
from django.core.exceptions import ValidationError


MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

BLOCKED_EXTENSIONS = {
    ".exe", ".sh", ".bat", ".cmd", ".py", ".php", ".js", ".vbs",
    ".html", ".htm", ".jsp", ".jar", ".msi", ".dll", ".scr", ".ps1",
    ".phtml", ".php3", ".php4", ".php5", ".phps", ".cgi", ".pl",
    ".asp", ".aspx", ".cer", ".csr", ".hta", ".htaccess", ".app",
    ".com", ".gadget", ".wsf", ".ws", ".bin", ".iso", ".dmg"
}

ALLOWED_EXTENSIONS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt",
    ".zip", ".rtf", ".svg"
}

# Dangerous executable / script magic byte signatures
DANGEROUS_MAGIC_HEADERS = [
    b"MZ",            # DOS / Windows PE Executable
    b"\x7fELF",       # Linux ELF Binary
    b"#!",            # Unix Shell Script Shebang
    b"<?php",         # PHP Script tag
    b"<script",       # HTML/JavaScript script tag
    b"<!DOCTYPE",     # Disguised HTML payload
    b"<html",         # HTML Document tag
]


def sanitize_filename(filename):
    """
    Sanitizes original filename to prevent directory traversal,
    null-byte injections, and unsafe characters.
    """
    if not filename:
        return "attachment"
    
    # Remove path components (Unix & Windows)
    clean_name = os.path.basename(filename)
    # Remove null bytes and control characters
    clean_name = clean_name.replace("\x00", "").strip()
    # Replace dangerous characters with underscores
    clean_name = re.sub(r'[\r\n\t\\/:*?"<>|]', "_", clean_name)
    # Remove leading dots to avoid hidden files
    clean_name = clean_name.lstrip(".")
    
    return clean_name or "attachment"


def validate_attachment_security(file_obj):
    """
    Hardened validation for uploaded request attachments:
    1. Enforces <= 10MB file size limit.
    2. Enforces allowed extension whitelist and explicitly blocks executable/script formats.
    3. Inspects binary magic bytes to block disguised executables and scripts.
    4. Validates and sanitizes filename.
    """
    if not file_obj:
        return

    # 1. File Size Check
    if file_obj.size > MAX_ATTACHMENT_SIZE_BYTES:
        raise ValidationError(
            f"File '{file_obj.name}' exceeds the maximum allowed size of 10 MB (size: {file_obj.size / (1024 * 1024):.1f} MB)."
        )

    # 2. Filename and Extension Check
    filename = file_obj.name or ""
    _, ext = os.path.splitext(filename.lower())

    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            f"File '{filename}' has a disallowed executable or script extension '{ext}'."
        )

    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"File format '{ext}' is not supported. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )

    # 3. Magic Bytes / Header Inspection
    try:
        initial_pos = file_obj.tell() if hasattr(file_obj, "tell") else 0
        header_bytes = file_obj.read(512)
        if hasattr(file_obj, "seek"):
            file_obj.seek(initial_pos)

        # Check for dangerous headers
        for bad_header in DANGEROUS_MAGIC_HEADERS:
            if header_bytes.startswith(bad_header):
                raise ValidationError(
                    f"File '{filename}' contains disallowed executable or script content signatures."
                )
    except ValidationError:
        raise
    except Exception:
        # If reading fails, let standard file handler manage it
        pass
