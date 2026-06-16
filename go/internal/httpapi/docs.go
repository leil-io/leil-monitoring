package httpapi

import "net/http"

// swaggerHTML renders Swagger UI from the public CDN against /openapi.json,
// reproducing the FastAPI /docs experience without a codegen dependency.
const swaggerHTML = `<!DOCTYPE html>
<html>
<head>
  <title>LeilFS Monitoring API</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({ url: "/openapi.json", dom_id: "#swagger-ui" });
  </script>
</body>
</html>`

func (a *API) handleDocs(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(swaggerHTML))
}

func (a *API) handleOpenAPI(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(openAPISpec))
}

// openAPISpec is a hand-maintained OpenAPI 3 description of the endpoints. The
// master host/port query parameters are shared by all data endpoints.
const openAPISpec = `{
  "openapi": "3.0.0",
  "info": {"title": "LeilFS Monitoring API", "version": "1.0.0"},
  "paths": {
    "/api/info": {"get": {"summary": "System info", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/chunkhealth": {"get": {"summary": "Chunk health", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/chunkservers": {"get": {"summary": "Chunk servers", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/disks": {"get": {"summary": "Disks", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/mounts": {"get": {"summary": "Mounts", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/metadataservers": {"get": {"summary": "Metadata servers", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/inotifiers": {"get": {"summary": "INotifiers", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/fscheckinfo": {"get": {"summary": "FS check info", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/chunkoperationsinfo": {"get": {"summary": "Chunk operations info", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/goals": {"get": {"summary": "Goals", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/exports": {"get": {"summary": "Exports", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/chunkmatrix": {"get": {"summary": "Chunk matrix", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/metaloggers": {"get": {"summary": "Metaloggers", "parameters": [{"$ref": "#/components/parameters/masterhost"}, {"$ref": "#/components/parameters/masterport"}], "responses": {"200": {"description": "OK"}}}},
    "/api/cgicharts": {"get": {"summary": "Chart data (PNG/CSV/GIF)", "parameters": [{"name": "id", "in": "query", "required": true, "schema": {"type": "integer"}}, {"name": "host", "in": "query", "schema": {"type": "string"}}, {"name": "port", "in": "query", "schema": {"type": "integer"}}], "responses": {"200": {"description": "OK"}}}}
  },
  "components": {
    "parameters": {
      "masterhost": {"name": "masterhost", "in": "query", "schema": {"type": "string"}},
      "masterport": {"name": "masterport", "in": "query", "schema": {"type": "integer"}}
    }
  }
}`
