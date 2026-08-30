import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from accounts.decorators import public_access
from .services.code_generation import CodeGenerationService


@login_required
@require_POST
def code_suggestion(request):
    try:
        data = json.loads(request.body)
        entity = data.get("entity")
        name = data.get("name")
        
        if not entity or name is None:
            return JsonResponse({"error": "Missing entity or name"}, status=400)
            
        tenant = request.tenant
        
        suggested_code = CodeGenerationService.generate(entity, name, tenant)
        
        return JsonResponse({"suggested_code": suggested_code})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@public_access
def openapi_schema(request):
    """
    Returns the complete OpenAPI 3.0 specification for Anukram's endpoints.
    """
    schema = {
        "openapi": "3.0.3",
        "info": {
            "title": "Anukram REST API",
            "version": "1.0.0",
            "description": "API documentation for Anukram Enterprise Workflow Management System. Provides system health monitoring, AI/rule-based code suggestions, and verifiable QR token verification."
        },
        "servers": [
            {
                "url": "https://anukram.onrender.com",
                "description": "Production Server"
            },
            {
                "url": "http://127.0.0.1:8000",
                "description": "Local Development Server"
            }
        ],
        "paths": {
            "/health/": {
                "get": {
                    "summary": "System & Database Health Check",
                    "description": "Returns operational status and PostgreSQL database connection check. Used by uptime monitors and load balancers.",
                    "responses": {
                        "200": {
                            "description": "Service is healthy and database is connected",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "healthy",
                                        "version": "1.0.0",
                                        "timestamp": "2026-08-30T17:15:00Z"
                                    }
                                }
                            }
                        },
                        "503": {
                            "description": "Database connection error",
                            "content": {
                                "application/json": {
                                    "example": {
                                        "status": "unhealthy",
                                        "version": "1.0.0",
                                        "timestamp": "2026-08-30T17:15:00Z"
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/code-suggestion/": {
                "post": {
                    "summary": "Generate Department / Designation Code Suggestion",
                    "description": "Generates a deterministic unique abbreviation code based on entity name and existing organization records.",
                    "security": [{"sessionAuth": []}],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["entity", "name"],
                                    "properties": {
                                        "entity": {"type": "string", "example": "department"},
                                        "name": {"type": "string", "example": "Engineering"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Generated code suggestion",
                            "content": {
                                "application/json": {
                                    "example": {"suggested_code": "ENG"}
                                }
                            }
                        },
                        "400": {"description": "Missing entity or name parameter"},
                        "403": {"description": "Authentication required"}
                    }
                }
            },
            "/verify/{token}/": {
                "get": {
                    "summary": "Public QR Permission Slip Verification",
                    "description": "Validates a UUIDv4 verification token embedded in a physical/digital PDF voucher. Returns live approval validity status.",
                    "parameters": [
                        {
                            "name": "token",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string", "format": "uuid"},
                            "description": "Verification token UUID"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Verification page rendered (VALID, INVALID, REVOKED, or EXPIRED)"
                        }
                    }
                }
            },
            "/export-audit-trail/": {
                "get": {
                    "summary": "Export Compliance Audit Trail (CSV)",
                    "description": "Exports a complete CSV audit log of all organization workflow submissions and approval chain events with UTF-8 BOM encoding for Excel.",
                    "security": [{"sessionAuth": []}],
                    "responses": {
                        "200": {
                            "description": "CSV audit file download",
                            "content": {
                                "text/csv": {
                                    "schema": {"type": "string", "format": "binary"}
                                }
                            }
                        },
                        "403": {"description": "Requires ORG_ADMIN or ADMIN role"}
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "sessionAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "sessionid"
                }
            }
        }
    }
    return JsonResponse(schema, json_dumps_params={"indent": 2})


@public_access
def api_docs(request):
    """
    Renders interactive Swagger UI documentation.
    """
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Anukram API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css">
    <link rel="icon" type="image/svg+xml" href="/static/img/favicon.svg">
    <style>
        body { margin: 0; background: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
        .swagger-ui .topbar { display: none; }
        .ank-header {
            background: #111827;
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #1f2937;
        }
        .ank-header a {
            color: #818cf8;
            text-decoration: none;
            font-size: 14px;
            font-weight: 600;
        }
        .ank-header a:hover { text-decoration: underline; }
        .ank-title {
            display: flex;
            align-items: center;
            gap: 12px;
            color: #ffffff;
            font-size: 18px;
            font-weight: 700;
        }
    </style>
</head>
<body>
    <div class="ank-header">
        <div class="ank-title">
            <svg width="24" height="24" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect width="32" height="32" rx="8" fill="#4F46E5"/>
                <path d="M9 16.5L16 9.5L23 16.5L20.5 19L16 14.5L11.5 19L9 16.5Z" fill="white"/>
                <circle cx="16" cy="10" r="1.5" fill="#38BDF8"/>
            </svg>
            Anukram API Reference
        </div>
        <div>
            <a href="/">← Return to App</a>
        </div>
    </div>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: "/api/openapi.json",
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ]
            });
        };
    </script>
</body>
</html>"""
    return HttpResponse(html_content, content_type="text/html")
